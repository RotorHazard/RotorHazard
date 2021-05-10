# RotorHazard 3.0.0 Release Notes

# RotorHazard 3.0.0 Release Notes

RotorHazard 3.0.0 provides many new features and fixes, including:

### Support for STM32 hardware
A RotorHazard timer can now be built using the new S32_BPill board (with a single STM32 processor instead of multiple Arduinos). This results in significant cost savings and fewer points of failure for new timer builds. RotorHazard maintains compatibility with all existing hardware.

### S32_BPill PCBs and case
See the [resources](https://github.com/RotorHazard/RotorHazard/blob/master/resources/README.md) section for information on the new [S32_BPill board](https://github.com/RotorHazard/RotorHazard/blob/master/resources/S32_BPill_PCB/README.md) and [3D-printable case](https://github.com/RotorHazard/RotorHazard/blob/master/resources/S32_BPill_case/README.md), including extensive documentation and build guides. STM32F1 and STM32F4 chips are supported on "Blue Pill" and "Black Pill" modules. Also check out the compact [RotorHazard 6 Node STM32 board](https://github.com/RotorHazard/RotorHazard/blob/master/resources/6_Node_BPill_PCB/README.md) (contributed by Aaron Smith).

### Data export
Export race data via the Database panel of the Settings page. Exporters are included for CSV and JSON formats with a variety of data types. Export uses a plugin system that will automatically load user-created exporter files for additional flexibility in data and format returned.

### Improved band / channel support
Selecting a frequency now stores the band/channel information instead of just numeric frequency. As a result, the user interface will display the selected band/channel when recalled (previously the first band/channel that matched the same frequency assignment was provided).

### Live graphic tuning
On the tuning dialog, drawing on the graph will immediately update enter and exit values. The "Tuning" button is removed for each node on the `Run` page as clicking on the graph itself opens this dialog.

### UI refresh
The UI has undergone a minor update, including a customized typeface. Heats listed on the `Run` page are sorted into classes. Disallowed actions no longer appear as UI options. The spacebar functions as a general-purpose hotkey for advancing the event.

### Cluster terminology has changed
A "Master" timer is now known as a "Primary" timer and "Slave" timers are now known as "Secondary" timers. Existing 'SLAVE' keys in the config.json file are still accepted, but their use is deprecated. Please migrate to 'SECONDARY' keys as documented in [Cluster.md](https://github.com/RotorHazard/RotorHazard/blob/3.0.0/doc/Cluster.md).

### End of support for Python 2
Python 2 is past end of life. RotorHazard 3.0 only officially supports Python 3 and some features will no longer function if run with Python 2. [See documentation for upgrade instructions](https://github.com/RotorHazard/RotorHazard/blob/3.0.0-beta.1/doc/Software%20Setup.md#5-install-python).

<a name="documentation"></a>
## Documentation
Documentation for RotorHazard 3.0.0 may be found at:
https://github.com/RotorHazard/RotorHazard/tree/3.0.0/doc

## Updates from RotorHazard 2.3

* Support for STM32 #482 #483 #538
* Data Export #456 #253
* Store band/channel #492 #499
* Add leader/winner tones #513
* Update relationship terminology #486
* Add support for hardware buzzer and status LED #538 #553
* Update UI for split/mirror connections #472
* Make important server message more prominent in UI #559
* Add space hotkey condition for race save action #564
* Improved database recovery
* Include customized UI typeface
* Removed UI for disallowed actions
* Make i2c bus index configurable #473
* Send peak duration instead of timestamp #432
* Favor best available data when history buffer is full #433
* Reduce i2c chill #409
* Fix Flask_SQLAlchemy dependency incompatibility
* Fix memory leak #527
* Fix issue with exporting unclassified races
* Fix cache issue with failed database load
* Fix file download under Python 3
* Fix filter time compensation #407
* Improve log outputs
* Add warning for split/cluster version mismatch
* Node firmware versioning #518
* Cleanup of language file #488
* Add STM32 build resources #513 #537
* Improve ease of install #555
* Bug fixes and stability improvements #561 #517 #548 #535
* Improve documentation #491 #495 #549 #558 #568
* Update frequency reference with updated Shark Byte assignments #570

## Installation / Upgrade Notes

To install RotorHazard on a new system, see the instructions in '[doc/Software Setup.md](https://github.com/RotorHazard/RotorHazard/blob/3.0.0/doc/Software%20Setup.md)'

To update an existing RotorHazard installation to this version:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/3.0.0 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-3.0.0 RotorHazard
rm temp.zip
cp RotorHazard.old/src/server/config.json RotorHazard/src/server/
cp RotorHazard.old/src/server/database.db RotorHazard/src/server/
```
The previous installation ends up in the 'RotorHazard.old' directory, which may be deleted or moved.

For RotorHazard the minimum version of Python supported is 3.5. If your Python is older than this, you should upgrade using the steps in the Software Setup document under "5. [Install Python](https://github.com/RotorHazard/RotorHazard/blob/main/doc/Software%20Setup.md#5-install-python)."

The RotorHazard server dependencies should also be updated (be patient, this command may take a few minutes):
```
cd ~/RotorHazard/src/server
sudo pip install --upgrade --no-cache-dir -r requirements.txt
```

## RotorHazard Node Code
New node code is provided with this version. As of this release, the RotorHazard node code supports both [Arduino-based](https://github.com/RotorHazard/RotorHazard/blob/master/src/node/readme_Arduino.md) and [S32_BPill](https://github.com/RotorHazard/RotorHazard/blob/master/resources/S32_BPill_PCB/README.md) boards.

For the S32_BPill board, the recommended method for installing the node firmware is to use the `Update Nodes` button (in the 'System' section on the 'Settings' page) on the RotorHazard web GUI.

Starting with this release the node code is now assigned a version, with this version at "1.1.4". The node-code version may be viewed in the Server Log, and via the "About RotorHazard" item in the drop-down menu.

## Issues
If you encounter a bug, please report it using the [Issues page on GitHub](https://github.com/RotorHazard/RotorHazard/issues). When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended (see below).

The Server Log may be displayed via the "View Server Log" item in the drop-down menu. Clicking on the "Select Text" button will select all the displayed log text, which may then be copied and pasted. Clicking on the "Download Logs" button will create and download a '.zip' archive file containing all available log files and the current configuration and database files.
