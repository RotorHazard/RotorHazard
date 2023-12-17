# RotorHazard 4.0.1 Release Notes

## Updates since v4.0.0

* Software Setup doc updates for venv etc (#815)
* Updated Event Setup Guide (#818)
* Updated User Guide
* Fixed leader proxy and RHAPI call for LED displays (#807)
* Fixed to prevent potential stall of speak queue processing
* Added Schedule Race shortcut key ('S')
* Improved plugins handling/logging when no Pillow library (#828)
* Eliminate dependency on "six" library (#805)

See the [release notes from v4.0.0](https://github.com/RotorHazard/RotorHazard/releases/tag/v4.0.0) for a list of the v4.0.0 changes since the v3.2.2 release. Full Changelog: https://github.com/RotorHazard/RotorHazard/compare/v3.2.0...v4.0.1

## Compatibility
RotorHazard v4.0.0 and later use an updated version of the socket library which is not compatible with releases before v4.0.0. All timers in a cluster (secondary/split timers, mirror timers) and socket-based interfaces must be updated to match. Because of this upgrade away from outdated and insecure code, **Delta5 emulation has ended with RotorHazard 3.2**.

<a name="documentation"></a>
## Documentation
Documentation for RotorHazard 4.0.1 may be found at:
https://github.com/RotorHazard/RotorHazard/tree/v4.0.1/doc

## Installation / Upgrade Notes
To install RotorHazard on a new system, see the instructions in '[doc/Software Setup.md](https://github.com/RotorHazard/RotorHazard/blob/v4.0.1/doc/Software%20Setup.md)'

To update an existing RotorHazard installation, see [Updating an Existing Installation](https://github.com/RotorHazard/RotorHazard/blob/v4.0.1/doc/Software%20Setup.md#updating-an-existing-installation). The current version code is `4.0.1`

## RotorHazard Node Code
No updates to the node code have been made since RotorHazard version 3.0.0 (the node-code version is 1.1.4).

## Issues
If you encounter a bug, please report it using the [Issues page on GitHub](https://github.com/RotorHazard/RotorHazard/issues). When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended (see below).

The Server Log may be displayed via the "View Server Log" item in the drop-down menu. Clicking on the "Select Text" button will select all the displayed log text, which may then be copied and pasted. Clicking on the "Download Logs" button will create and download a '.zip' archive file containing all available log files and the current configuration and database files.