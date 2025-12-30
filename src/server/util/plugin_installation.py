"""
Plugin installation management
"""

import io
import json
import os
import shutil
import sys
import zipfile
from dataclasses import MISSING, asdict, dataclass, field, fields
from enum import IntEnum
from pathlib import Path
from typing import Any, TypeVar
import hashlib
import logging
from typing import Callable

import requests
from gevent import pool, subprocess
from packaging import version

DEFAULT_DATA_URI = "https://rhcp.hazardcreative.com/v1/plugin/data.json"
DEFAULT_CATEGORIES_URI = "https://rhcp.hazardcreative.com/v1/plugin/categories.json"
DEFAULT_TIMEOUT = 10

T = TypeVar("T")

logger = logging.getLogger(__file__)


class _PluginStatus(IntEnum):
    """
    Remote plugin installation or update status
    """

    UNKNOWN = 1
    NOT_INSTALLED = 2
    PRE_RELEASE_UPDATE = 3
    RELEASE_UPDATE = 4
    NO_UPDATE = 5


class PluginInstallationError(Exception):
    """
    Exceptions signalling an error in the plugin installation
    process
    """

    def __init__(self, message, domain: str):
        self.message = message
        self.domain = domain
        super().__init__(self.message)


class InvalidRHAPIVersion(PluginInstallationError):
    """
    Exception signalling that the minimum RHAPI version was not
    met when installing a plugin
    """


@dataclass(frozen=True)
class Manifest:
    domain: str
    name: str
    description: str
    required_rhapi_version: str
    version: str
    dependencies: list[str] = field(default_factory=list)
    author: str | None = None
    author_uri: str | None = None
    documentation_uri: str | None = None
    zip_filename: str | None = None
    license: str | None = None
    license_uri: str | None = None


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    size: int
    download_count: int
    sha256: str | None = None


@dataclass(frozen=True)
class Release:
    tag_name: str
    published_at: str
    prerelease: bool
    assets: list[ReleaseAsset] = field(default_factory=list)


@dataclass
class RemoteData:
    manifest: Manifest
    releases: list[Release]
    repository: str
    last_version: str | None = None
    last_prerelease: str | None = None
    reload_required: bool = False
    update_status: _PluginStatus = _PluginStatus.UNKNOWN

    @property
    def domain(self):
        return self.manifest.domain


@dataclass
class LocalData:
    manifest: Manifest
    reload_required: bool = False
    update_status: _PluginStatus = _PluginStatus.UNKNOWN

    @property
    def domain(self):
        return self.manifest.domain

    @property
    def version(self):
        return self.manifest.version


def parse_dict_to_dataclass(cls: type[T], data: dict[str, Any]) -> T:
    """
    Recursively parses a dictionary into a dataclass instance.
    """
    if not hasattr(cls, "__dataclass_fields__"):
        raise TypeError(f"{cls.__name__} is not a dataclass.")

    field_values: dict[str, T | list[T]] = {}
    for field_info in fields(cls):  # type: ignore
        field_name = field_info.name
        field_type: type = field_info.type  # type: ignore

        if field_name in data:
            value = data[field_name]
            if hasattr(field_type, "__dataclass_fields__") and isinstance(value, dict):
                field_values[field_name] = parse_dict_to_dataclass(field_type, value)
            elif (
                isinstance(value, list)
                and hasattr(field_type, "__args__")
                and hasattr(field_type.__args__[0], "__dataclass_fields__")
            ):
                nested_dataclass_type = field_type.__args__[0]
                field_values[field_name] = [
                    parse_dict_to_dataclass(nested_dataclass_type, item)
                    for item in value
                ]
            else:
                field_values[field_name] = value
        elif field_info.default is not MISSING:
            field_values[field_name] = field_info.default
        elif field_info.default_factory is not MISSING:
            field_values[field_name] = field_info.default_factory()
        else:
            raise ValueError(f"Missing required field: {field_name}")

    return cls(**field_values)


class PluginInstallationManager:
    """
    Plugin installation and update management
    """

    def __init__(
        self,
        plugin_dir: Path,
        remote_config: dict,
        /,
        api_version: str,
        notify_cb: Callable[[str], None],
    ):
        if not plugin_dir.exists():
            raise FileNotFoundError(f"{plugin_dir} does not exist")

        if not plugin_dir.is_dir():
            raise TypeError(f"{plugin_dir} is not a directory")

        self._session = requests.Session()
        self._remote_plugin_data: dict[str, RemoteData] = {}
        self._local_plugin_data: dict[str, LocalData] = {}
        self._prerelease_mapping: dict[str, bool] = {}
        self._categories: dict[str, list[str]] = {}
        self._api_version = version.parse(api_version)
        self._notify = notify_cb
        self.update_available = False
        self._pool = pool.Pool(10)

        self._plugin_dir = Path(plugin_dir)
        self.load_local_plugin_data()

        data_uri = remote_config.get("data_uri", None)
        if data_uri is None:
            data_uri = DEFAULT_DATA_URI
        self._remote_data_uri = data_uri

        categories_uri = remote_config.get("categories_uri", None)
        if categories_uri is None:
            categories_uri = DEFAULT_CATEGORIES_URI
        self._remote_category_uri = categories_uri

    def load_remote_plugin_data(self):
        """
        Load remote plugin data
        """
        data = self._session.get(self._remote_data_uri, timeout=DEFAULT_TIMEOUT)

        for plugin in dict(data.json()).values():
            self._fetch_remote_plugin_data(plugin)

        data = self._session.get(
            self._remote_category_uri,
            timeout=DEFAULT_TIMEOUT,
        )

        self._categories = data.json()

    def _fetch_remote_plugin_data(self, plugin_data: dict):
        """
        Parse remote plugin data and store the result
        """
        data = parse_dict_to_dataclass(RemoteData, plugin_data)
        self._remote_plugin_data.update({data.manifest.domain: data})

    def load_local_plugin_data(self) -> None:
        """
        Loads local plugin data

        :raises FileNotFoundError: The specific plugin directory was not found
        :raises TypeError: The
        """
        self._pool.map(self._read_plugin_data, self._plugin_dir.iterdir())

    def _read_plugin_data(
        self, plugin_path: Path, *, reload_required: bool = False
    ) -> None:
        """
        Read the manifest data from an installed plugin

        :param plugin_path: The path of the plugin
        :param reload_required: Whether the system needs to reload to enable the
        plugin or not
        """
        manifest_path = plugin_path.joinpath("manifest.json")

        if not manifest_path.exists():
            return

        with open(manifest_path, "r", encoding="utf-8") as file:
            data = json.load(file)

            if "domain" not in data:
                data["domain"] = plugin_path.stem

            manifest = parse_dict_to_dataclass(Manifest, data)
            plugin_data = LocalData(manifest, reload_required)

        self._local_plugin_data.update({plugin_data.domain: plugin_data})

    def apply_update_statuses(self) -> None:
        """
        Generates the install and update status of each plugin
        """
        for value in self._remote_plugin_data.values():
            self._apply_update_status(value)

    def _apply_update_status(self, remote_data: RemoteData) -> None:
        """
        Gets the install and update status of a remote plugin

        :param plugin_data: The remote data
        :raises ValueError: Local plugin data not generated
        :return: Status of plugin install
        """
        remote_version = remote_data.last_version
        domain = remote_data.domain

        if domain not in self._local_plugin_data:
            return

        local_data = self._local_plugin_data[domain]
        local_version = local_data.version

        if remote_version is not None and local_version is not None:
            remote_version_ = version.parse(remote_version)
            local_version_ = version.parse(local_version)

            if remote_version_ > local_version_ and remote_version_.is_prerelease:
                remote_data.update_status = local_data.update_status = (
                    _PluginStatus.PRE_RELEASE_UPDATE
                )
                self.update_available = True
            elif remote_version_ > local_version_:
                remote_data.update_status = local_data.update_status = (
                    _PluginStatus.RELEASE_UPDATE
                )
                self.update_available = True
            else:
                remote_data.update_status = _PluginStatus.NO_UPDATE

        elif remote_version is not None and local_version is None:
            remote_data.update_status = _PluginStatus.NOT_INSTALLED

        else:
            remote_data.update_status = _PluginStatus.UNKNOWN

    def download_plugin(self, domain: str, tag: str | None = None):
        """
        Downloads the latest release of the plugin defined by
        the domain from GitHub

        :param domain: The plugin's domain
        :param tag: The version tag of the plugin to download, defaults to None
        :raises ValueError: Lacking remote data
        :raises PluginInstallationError: Lacking remote data
        """
        try:
            plugin_data = self._remote_plugin_data[domain]
        except KeyError as ex:
            raise ValueError("Plugin data was not found") from ex

        if tag is None and plugin_data.last_version is not None:
            tag = plugin_data.last_version
        elif tag is None and plugin_data.last_prerelease is not None:
            tag = plugin_data.last_prerelease
        elif tag is None:
            raise PluginInstallationError(
                "Unable to determine the plugin version to download", domain
            )

        for release_ in plugin_data.releases:
            if release_.tag_name == tag:
                break
        else:
            raise PluginInstallationError(
                "Remote data does not contain a matching release version", domain
            )

        try:
            self._download_and_install_plugin(
                plugin_data,
                release_,
            )
        except requests.Timeout as ex:
            raise PluginInstallationError(
                "Timed out downloading plugin data", domain
            ) from ex

        plugin_data.reload_required = True
        self._read_plugin_data(self._plugin_dir.joinpath(domain), reload_required=True)

        self.apply_update_statuses()

    def _download_and_install_plugin(
        self,
        plugin_data: RemoteData,
        release: Release,
    ) -> None:
        """
        Downloads the zip of the plugin version from Github. If successful,
        remove the prexisting folder for the plugin and install the new data.

        :param plugin_data: The remote plugin data
        :param release: The release of the plugin to install
        """
        repo = plugin_data.repository
        from_asset = False
        asset: ReleaseAsset | None

        for asset in release.assets:
            if asset.name == f"{plugin_data.domain}.zip":
                from_asset = True
                break
        else:
            asset = None
            if plugin_data.manifest.zip_filename is not None:
                from_asset = True

        if from_asset and asset is not None:
            url = f"https://github.com/{repo}/releases/download/{release.tag_name}/{asset.name}"
            response = self._session.get(url, timeout=DEFAULT_TIMEOUT)

            sha256_hash = hashlib.sha256()
            sha256_hash.update(response.content)

            if asset.sha256 is not None and sha256_hash.hexdigest() != asset.sha256:
                raise PluginInstallationError(
                    "Downloaded asset doesn't match expected hash", plugin_data.domain
                )
            elif asset.sha256 is not None:
                logger.info("Downloaded asset hash for %s matches", plugin_data.domain)
            else:
                logger.warning(
                    "Downloaded asset for %s does not provide a hash",
                    plugin_data.domain,
                )

        elif from_asset:
            file_name = plugin_data.manifest.zip_filename
            url = f"https://github.com/{repo}/releases/download/{release.tag_name}/{file_name}"
            response = self._session.get(url, timeout=DEFAULT_TIMEOUT)

        else:
            url = f"https://github.com/{repo}/archive/refs/tags/{release.tag_name}.zip"
            response = self._session.get(url, timeout=DEFAULT_TIMEOUT)

        self.delete_plugin_dir(plugin_data.domain)

        try:
            self._install_plugin_data(plugin_data.domain, response.content)
        except (PluginInstallationError, InvalidRHAPIVersion):
            self.delete_plugin_dir(plugin_data.domain)
            raise

    def delete_plugin_dir(self, domain: str) -> None:
        """
        Removes a plugin's directory from the plugin folder. Used to
        uninstall plugins.

        :param plugin_dir: The plugin domain to clean
        """
        plugin_dir = self._plugin_dir.joinpath(domain)

        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        if domain in self._local_plugin_data:
            del self._local_plugin_data[domain]

        self.apply_update_statuses()

    def _install_plugin_data(self, domain: str, download: bytes) -> None:
        """
        Installs downloaded plugin data to the domain's folder

        :param domain: The plugin's domain
        :param download: The downloaded content
        """
        plugin_dir = Path(self._plugin_dir).joinpath(domain)
        identifier = f"{domain}/"

        with zipfile.ZipFile(io.BytesIO(download), "r") as zip_data:
            for file in zip_data.filelist:
                name = file.filename

                if name.find(identifier) != -1 and not name.endswith((identifier, "/")):
                    save_stem = file.filename.split(identifier)[-1]
                    save_name = plugin_dir.joinpath(save_stem)

                    if directory := os.path.dirname(save_name):
                        os.makedirs(directory, exist_ok=True)

                    file_data = zip_data.read(file)
                    save_name.write_bytes(file_data)

                    if name.endswith("manifest.json"):
                        self._process_manifest(domain, file_data)

    def _process_manifest(self, domain: str, file_data: bytes) -> None:
        """
        Evaluate data in the manifest file for plugin installation

        :param domain: The domain used for the plugin
        :param file_data: Manifest file as bytes
        :raises PluginInstallationError: Error when installing the plugin
        """
        data: dict = json.loads(file_data)
        manifest = parse_dict_to_dataclass(Manifest, data)

        min_version = version.parse(manifest.required_rhapi_version)
        if self._api_version < min_version:
            raise InvalidRHAPIVersion(
                (
                    "The plugin version attempting to be install "
                    "requires a newer version of RotorHazard than "
                    "what is currently installed."
                ),
                domain,
            )

        if manifest.dependencies:
            self._notify(
                (
                    "Installing additional plugin dependencies. "
                    "Please wait for installation completion."
                )
            )
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", *manifest.dependencies],
                    check=True,
                )
            except subprocess.CalledProcessError as ex:
                raise PluginInstallationError(
                    "Failed to install dependencies", domain
                ) from ex

    def _update_with_check(self, data: RemoteData) -> None:
        """
        Checks to see if the plugin has an update avaliable.
        If it does, download the new version.

        :param data: The plugin data and mode to check against
        """
        if data.update_status == _PluginStatus.RELEASE_UPDATE:
            self.download_plugin(data.domain)

    def mass_update_plugins(self) -> None:
        """
        Performs an update on all plugins if an update is avalible.
        This will only upgrade plugins to their newest stable version.
        """

        remote_plugins = self._remote_plugin_data.values()
        self._pool.map(self._update_with_check, remote_plugins)

    def get_local_display_data(self) -> dict[str, dict]:
        """
        Generates a compilation of local plugin data for the
        user interface

        :return: Compilation of plugin data
        """
        return {
            domain: asdict(data) for domain, data in self._local_plugin_data.items()
        }

    def get_display_data(self) -> dict[str, dict]:
        """
        Generates a compilation of remote plugin data for the
        user interface

        :return: Compilation of plugin data
        """
        return {
            domain: asdict(data) for domain, data in self._remote_plugin_data.items()
        }

    def get_remote_categories(self) -> dict[str, list[str]]:
        """
        Lists the categories fetched from the remote repository

        :return: Compilation of categories
        """
        return self._categories

    def _install_from_upload(self, file: bytes, domain: str) -> None:
        """
        Do the work of installing the plugin from a zip file.

        :param file: The zip file to use for the install
        :param domain: The domain to install the plugin under
        """

        self.delete_plugin_dir(domain)
        self._install_plugin_data(domain, file)

        path = Path(self._plugin_dir).joinpath(domain)
        self._read_plugin_data(path, reload_required=True)

    def install_from_upload(self, file: bytes) -> None:
        """
        Installs a plugin(s) from a zip file.

        :param file: The zipfile as bytes
        :raises zipfile.BadZipFile: Uploaded file is not a valid
        zip file
        :raises JSONDecodeError: JSON file is not valid
        :raises KeyError: Domain not in manifest file
        """
        with zipfile.ZipFile(io.BytesIO(file), "r") as zip_data:
            manifest_found = False
            init_domain = None

            for name in zip_data.namelist():
                if name.endswith("/manifest.json"):
                    manifest_found = True
                    domain = Path(name).parent.stem
                    self._install_from_upload(file, domain)

                elif name.endswith("/__init__.py"):
                    init_domain = Path(name).parent.stem

            if not manifest_found and init_domain is not None:
                self._install_from_upload(file, init_domain)

            elif not manifest_found:
                raise ValueError("Uploaded plugin is invalid")

        self.apply_update_statuses()
