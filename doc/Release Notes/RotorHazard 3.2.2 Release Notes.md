# RotorHazard 3.2.2 Release Notes

## Updates since [3.2.1](RotorHazard%203.2.1%20Release%20Notes.md)

* Added zero-delay staging when race is started via Delta5 emulation (fixes short holeshots LiveTime)
* Supply a consistent zero point for Delta5 emulation (LiveTime results now exactly match RotorHazard results)
* Fixed marshaling a race with no/secondary format
* Fixed stopping a race multiple times
* Fixed announcing an unassigned pilot

See [release notes from 3.2.0](RotorHazard%203.2.0%20Release%20Notes.md) for more information on this version.

Full Changelog: https://github.com/RotorHazard/RotorHazard/compare/v3.2.1...v3.2.2

<a name="documentation"></a>
## Documentation
Documentation for RotorHazard 3.2.2 may be found at:
https://github.com/RotorHazard/RotorHazard/tree/v3.2.2/doc

## Installation / Upgrade Notes
To install RotorHazard on a new system, see the instructions in '[doc/Software Setup.md](https://github.com/RotorHazard/RotorHazard/blob/v3.2.2/doc/Software%20Setup.md)'

To update an existing RotorHazard installation to this version:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/v3.2.2 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-3.2.2 RotorHazard
rm temp.zip
cp RotorHazard.old/src/server/config.json RotorHazard/src/server/
cp RotorHazard.old/src/server/database.db RotorHazard/src/server/
```
The previous installation ends up in the 'RotorHazard.old' directory, which may be deleted or moved.

The minimum version of Python supported is 3.5. If your Python is older than this, you should upgrade using the steps in the Software Setup document under "5. [Install Python](https://github.com/RotorHazard/RotorHazard/blob/main/doc/Software%20Setup.md#5-install-python)."

## RotorHazard Node Code
No updates to the node code have been made since RotorHazard version 3.0.0 (the node-code version is 1.1.4).

## Issues
If you encounter a bug, please report it using the [Issues page on GitHub](https://github.com/RotorHazard/RotorHazard/issues). When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended (see below).

The Server Log may be displayed via the "View Server Log" item in the drop-down menu. Clicking on the "Select Text" button will select all the displayed log text, which may then be copied and pasted. Clicking on the "Download Logs" button will create and download a '.zip' archive file containing all available log files and the current configuration and database files.