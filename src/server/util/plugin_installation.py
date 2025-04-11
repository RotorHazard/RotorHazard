"""
Plugin installation management
"""

import os
import io
import sys
import json
import shutil
import zipfile
from enum import IntEnum
from pathlib import Path
from typing import Any, Union

import requests
from gevent import subprocess, pool
from packaging import version

DEFAULT_DATA_URI = "https://rhcp.hazardcreative.com/v1/plugin/data.json"
DEFAULT_CATEGORIES_URI = "https://rhcp.hazardcreative.com/v1/plugin/categories.json"

class _PluginStatus(IntEnum):
    """
    Remote plugin installation or update status
    """

    UNKNOWN = 1
    NOT_INSTALLED = 2
    PRE_RELEASE_UPDATE = 3
    RELEASE_UPDATE = 4
    NO_UPDATE = 5


class PluginInstallationManager:
    """
    Plugin installation and update management
    """

    _session: requests.Session
    _remote_plugin_data: dict[str, dict]
    _local_plugin_data: dict[str, Any]
    _prerelease_mapping: dict[str, bool]
    _categories: list[str]
    update_avaliable: bool = False

    def __init__(self, plugin_dir: Path, remote_config: dict):

        if not plugin_dir.exists():
            raise FileNotFoundError(f"{plugin_dir} does not exist")

        if not plugin_dir.is_dir():
            raise TypeError(f"{plugin_dir} is not a directory")

        self._session = requests.Session()
        self._remote_plugin_data = {}
        self._local_plugin_data = {}
        self._prerelease_mapping = {}
        self._categories = []

        self._plugin_dir = plugin_dir
        self.load_local_plugin_data()

        data_uri = remote_config.get('data_uri', None)
        if data_uri is None:
            data_uri = DEFAULT_DATA_URI
        self._remote_data_uri = data_uri
        
        categories_uri = remote_config.get('categories_uri', None)
        if categories_uri is None:
            categories_uri = DEFAULT_CATEGORIES_URI
        self._remote_category_uri = categories_uri

    def load_remote_plugin_data(self):
        """
        Load remote plugin data
        """
        data = self._session.get(
            self._remote_data_uri, timeout=5
        )

        pool_ = pool.Pool(10)
        pool_.map(self._fetch_remote_plugin_data, dict(data.json()).values())

        data = self._session.get(
            self._remote_category_uri, timeout=5,
        )

        self._categories = data.json()

    def _fetch_remote_plugin_data(self, plugin_data: dict):
        plugin_data["reload_required"] = False

        self._remote_plugin_data.update({plugin_data["manifest"]["domain"]: plugin_data})

    def load_local_plugin_data(self) -> None:
        """
        Loads local plugin data

        :raises FileNotFoundError: The specific plugin directory was not found
        :raises TypeError: The
        """
        pool_ = pool.Pool(10)
        pool_.map(self._read_plugin_data, self._plugin_dir.iterdir())

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
            data["reload_required"] = reload_required
            data["update_status"] = _PluginStatus.NO_UPDATE

            if "domain" in data:
                data_ = {data["domain"]: data}
            else:
                data_ = {plugin_path.stem: data}

        self._local_plugin_data.update(data_)

    def apply_update_statuses(self) -> None:
        """
        Generates the install and update status of each plugin
        """
        for value in self._remote_plugin_data.values():
            self._apply_update_status(value)

    def _apply_update_status(self, plugin_data: dict[str, Any]) -> None:
        """
        Gets the install and update status of a remote plugin

        :param plugin_data: The remote data
        :raises ValueError: Local plugin data not generated
        :return: Status of plugin install
        """
        remote_version = plugin_data.get("last_version")
        domain: Union[str, None] = plugin_data.get("domain")

        if domain is not None and domain in self._local_plugin_data:
            local_data: dict[str, Any] = self._local_plugin_data[domain]
            local_version = local_data.get("version")
        else:
            local_version = None

        if remote_version is not None and local_version is not None:
            remote_version_ = version.parse(remote_version)
            local_version_ = version.parse(local_version)

            if remote_version_ > local_version_ and remote_version_.is_prerelease:
                plugin_data["update_status"] = local_data["update_status"] = (
                    _PluginStatus.PRE_RELEASE_UPDATE
                )
                self.update_avaliable = True
            elif remote_version_ > local_version_:
                plugin_data["update_status"] = local_data["update_status"] = (
                    _PluginStatus.RELEASE_UPDATE
                )
                self.update_avaliable = True
            else:
                plugin_data["update_status"] = _PluginStatus.NO_UPDATE

        elif remote_version is not None and local_version is None:
            plugin_data["update_status"] = _PluginStatus.NOT_INSTALLED

        else:
            plugin_data["update_status"] = _PluginStatus.UNKNOWN

    def download_plugin(self, domain: str, *, allow_prerelease: bool = False) -> None:
        """
        Downloads the latest release of the plugin defined by
        the domain from GitHub

        :param domain: The plugin's domain
        :raises ValueError: Lacking remote data
        :param allow_prerelease: Update to prerelease version, defaults to False
        """
        try:
            plugin_data = self._remote_plugin_data[domain]
        except KeyError as ex:
            raise ValueError("Plugin data was not found") from ex

        repo = plugin_data.get("repository")
        last_version = plugin_data.get("last_version")
        pre_version = plugin_data.get("last_prerelease")

        manifest: dict = plugin_data["manifest"]
        zip_filename = manifest.get("zip_filename")

        if last_version is not None and pre_version is not None and allow_prerelease:
            if version.parse(last_version) < version.parse(pre_version):
                download_version = pre_version
            else:
                download_version = last_version
        else:
            download_version = last_version

        if repo is None or download_version is None:
            raise ValueError("Plugin metadata is not valid")

        self._download_and_install_plugin(
            repo, download_version, domain, zip_filename
        )

        plugin_data["reload_required"] = True
        self._read_plugin_data(
            Path(self._plugin_dir).joinpath(domain), reload_required=True
        )

        self.apply_update_statuses()

    def _download_and_install_plugin(
        self,
        repo: str,
        version_: str,
        domain: str,
        zip_filename: Union[str, None],
    ) -> None:
        """
        Downloads the zip of the plugin version from Github. If successful,
        remove the prexisting folder for the plugin and install the new data.

        :param repo: The plugin repo
        :param version_: The version of the plugin to install
        :param domain: The domain identifier of the plugin
        """

        if zip_filename is not None:
            url = (
                f"https://github.com/{repo}/releases/download/{version_}/{zip_filename}"
            )
        else:
            url = f"https://github.com/{repo}/archive/refs/tags/{version_}.zip"

        response = self._session.get(url, timeout=10)

        self.delete_plugin_dir(domain)
        self._install_plugin_data(domain, response.content)

    def delete_plugin_dir(self, domain: str) -> None:
        """
        Removes a plugin's directory from the plugin folder. Used to
        uninstall plugins.

        :param plugin_dir: The plugin domain to clean
        """
        plugin_dir = Path(self._plugin_dir).joinpath(domain)

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
                        self._install_dependencies(file_data)

    def _install_dependencies(self, manifest: bytes) -> None:
        """
        Loads the manifest data and install the dependencies
        through pip

        :param manifest: Manifest file as bytes
        """

        manifest_: dict = json.loads(manifest)
        depends = manifest_.get("dependencies", None)

        if depends is not None:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", *depends], check=True
            )

    def _update_with_check(self, data: dict) -> None:
        """
        Checks to see if the plugin has an update avaliable.
        If it does, download the new version.

        :param data: The plugin data and mode to check against
        """
        status = data.get("update_status")

        if status is not None:

            if status == _PluginStatus.RELEASE_UPDATE:
                self.download_plugin(data["domain"])

            elif status == _PluginStatus.PRE_RELEASE_UPDATE:
                domain = data["domain"]
                if self._prerelease_mapping.get(domain, False):
                    self.download_plugin(domain, allow_prerelease=True)

    def mass_update_plugins(
        self, *, prerelease_mapping: Union[dict[str, bool], None] = None
    ) -> None:
        """
        Update all avaliable plugins. Only updates plugins if they are already
        installed.

        The mapping for this fucntion should be in the form of
        {str(domain) : bool(allow_prerelease_install)}
        """
        if prerelease_mapping is not None:
            self._prerelease_mapping = prerelease_mapping

        remote_plugins = self._remote_plugin_data.values()

        pool_ = pool.Pool(10)
        pool_.map(self._update_with_check, remote_plugins)

    def get_local_display_data(self) -> dict[str, dict]:
        """
        Generates a compilation of local plugin data for the
        user interface

        :return: Compilation of plugin data
        """

        return self._local_plugin_data

    def get_display_data(self) -> dict[str, dict]:
        """
        Generates a compilation of remote plugin data for the
        user interface

        :return: Compilation of plugin data
        """

        return self._remote_plugin_data

    def get_remote_categories(self) -> dict[str, dict]:
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
                raise ValueError("Invalid uploaded plugin")

        self.apply_update_statuses()
