# RotorHazard 3.1.1 Release Notes

## Updates since 3.1.0

 * Fixed issue adding nodes to existing setup #637

See [release notes from 3.1.0](https://github.com/RotorHazard/RotorHazard/releases/tag/3.1.0) for more information on this version.

<a name="documentation"></a>
## Documentation

Documentation for RotorHazard 3.1.1 may be found at:
https://github.com/RotorHazard/RotorHazard/tree/3.1.1/doc

## Installation / Upgrade Notes

To install RotorHazard on a new system, see the instructions in '[doc/Software Setup.md](https://github.com/RotorHazard/RotorHazard/blob/3.1.1/doc/Software%20Setup.md)'

To update an existing RotorHazard installation to this version:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/3.1.1 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-3.1.1 RotorHazard
rm temp.zip
cp RotorHazard.old/src/server/config.json RotorHazard/src/server/
cp RotorHazard.old/src/server/database.db RotorHazard/src/server/
```
The previous installation ends up in the 'RotorHazard.old' directory, which may be deleted or moved.

The minimum version of Python supported is 3.5. If your Python is older than this, you should upgrade using the steps in the Software Setup document under "5. [Install Python](https://github.com/RotorHazard/RotorHazard/blob/main/doc/Software%20Setup.md#5-install-python)."

The RotorHazard server dependencies should also be updated (be patient, this command may take a few minutes):
```
cd ~/RotorHazard/src/server
sudo pip install --upgrade --no-cache-dir -r requirements.txt
```

## RotorHazard Node Code
No updates to the node code have been made since RotorHazard version 3.0.0 (the node-code version is 1.1.4).

## Issues
If you encounter a bug, please report it using the [Issues page on GitHub](https://github.com/RotorHazard/RotorHazard/issues). When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended (see below).

The Server Log may be displayed via the "View Server Log" item in the drop-down menu. Clicking on the "Select Text" button will select all the displayed log text, which may then be copied and pasted. Clicking on the "Download Logs" button will create and download a '.zip' archive file containing all available log files and the current configuration and database files.