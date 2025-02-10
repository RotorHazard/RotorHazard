"""
Plugin installation management
"""

import os
import io
import json
import shutil
import zipfile
import copy
from enum import IntEnum
from pathlib import Path
from typing import Any, Union

import requests
from gevent import pool
from packaging import version

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

    _session = requests.Session()
    _remote_plugin_data: dict[str, dict] = {}
    _local_plugin_data: dict[str, Any] = {}
    _prerelease_mapping: dict[str, bool] = {}

    def __init__(self, plugin_dir: Path):

        if not plugin_dir.exists():
            raise FileNotFoundError(f"{plugin_dir} does not exist")
        elif not plugin_dir.is_dir():
            raise TypeError(f"{plugin_dir} is not a directory")

        self._plugin_dir = plugin_dir
        self.load_local_plugin_data()

    def load_remote_plugin_data(self):
        """
        Load remote plugin data
        """
        data = self._session.get(
            "https://rh-data.dutchdronesquad.nl/v1/plugin/data.json", timeout=5
        )

        for plugin in dict(data.json()).values():
            for key, value in dict(plugin["manifest"]).items():
                plugin[key] = value

            del plugin["manifest"]

            self._remote_plugin_data.update({plugin["domain"]: plugin})

    def load_local_plugin_data(self) -> None:
        """
        Loads local plugin data

        :raises FileNotFoundError: The specific plugin directory was not found
        :raises TypeError: The
        """
        pool_ = pool.Pool(10)
        pool_.map(self._read_plugin_data, self._plugin_dir.iterdir())

    def _read_plugin_data(self, plugin_path: Path) -> None:
        """
        Read the manifest data from an installed plugin

        :param plugin_path: The path of the plugin
        :return: The loaded manifest data
        """
        manifest_path = plugin_path.joinpath("manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as file:
            data = json.load(file)

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
                plugin_data["update_status"] = _PluginStatus.PRE_RELEASE_UPDATE
            elif remote_version_ > local_version_:
                plugin_data["update_status"] = _PluginStatus.RELEASE_UPDATE
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
        for plugin_data in self._remote_plugin_data.values():
            if domain == plugin_data.get("domain"):
                break
        else:
            raise ValueError("Plugin was not found")

        repo = plugin_data.get("repository")
        version_ = plugin_data.get("last_version")
        pre_version = plugin_data.get("last_prerelease")

        zip_release = plugin_data.get("zip_release ")
        zip_filename = plugin_data.get("zip_filename")

        if version_ is not None and pre_version is not None and allow_prerelease:
            if version.parse(version_) < version.parse(pre_version):
                version_ = pre_version

        if repo is not None and version_ is not None:
            self._download_and_install_plugin(
                repo, version_, domain, zip_release, zip_filename
            )
        else:
            raise ValueError("Plugin metadata is not valid")

    def _download_and_install_plugin(
        self,
        repo: str,
        version_: str,
        domain: str,
        zip_release: Union[bool, None],
        zip_filename: Union[str, None],
    ) -> None:
        """
        Downloads the zip of the plugin version from Github. If successful,
        remove the prexisting folder for the plugin and install the new data.

        :param repo: The plugin repo
        :param version_: The version of the plugin to install
        :param domain: The domain identifier of the plugin
        """

        if zip_release and zip_filename is not None:
            url = (
                f"https://github.com/{repo}/releases/download/{version_}/{zip_filename}"
            )
        else:
            url = f"https://github.com/{repo}/archive/refs/tags/{version_}.zip"

        response = self._session.get(url, timeout=10)

        self._delete_plugin_dir(domain)
        self._install_plugin_data(domain, response.content)

    def _delete_plugin_dir(self, domain: str) -> None:
        """
        Generate a clean directory to install the plugin into.

        :param plugin_dir: The plugin directory to setup
        """
        plugin_dir = Path(self._plugin_dir).joinpath(domain)
        
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

    def _install_plugin_data(self, domain: str, download: bytes):
        """
        Installs downloaded plugin data to the domain's folder

        :param domain: The plugin's domain
        :param download: The downloaded content
        """
        plugin_dir = Path(self._plugin_dir).joinpath(domain)
        identifier = f"custom_plugins/{domain}/"

        with zipfile.ZipFile(io.BytesIO(download), "r") as zip_data:
            for file in zip_data.filelist:
                fname = file.filename

                if fname.find(identifier) != -1 and not fname.endswith(identifier):
                    save_stem = file.filename.split(identifier)[-1]
                    save_name = plugin_dir.joinpath(save_stem)

                    directory = os.path.dirname(save_name)
                    if directory:
                        os.makedirs(directory, exist_ok=True)

                    with open(save_name, "wb") as file_:
                        file_.write(zip_data.read(file))

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
        self, *, prerelease_mapping: Union[dict[str, bool] , None] = None
    ) -> None:
        """
        Update all avaliable plugins. Only updates plugins if they are already
        installed.
        """
        if prerelease_mapping is not None:
            self._prerelease_mapping = prerelease_mapping

        remote_plugins = self._remote_plugin_data.values()

        pool_ = pool.Pool(10)
        pool_.map(self._update_with_check, remote_plugins)

    def get_display_data(self) -> dict[str, dict]:
        """
        Generates a compilation of remote plugin data for the
        user interface

        :return: Compilation of plugin data
        """

        return self._remote_plugin_data