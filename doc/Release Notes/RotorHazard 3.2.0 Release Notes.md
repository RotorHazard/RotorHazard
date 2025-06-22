# RotorHazard 3.2.0 Release Notes

## New features and important fixes

### New race format extensions
Extended staging sequence options allow more control of staging tones and random delay. Laps stop automatically counting once a race concludes. Automatic race stop after configurable grace period.

### Actions
Assign effects to timer events to automate common tasks. For example, assign speech to the "pilot done" event for automatic announcement of each pilot's end. Available action effects will be extended in future versions, and plugins may supply new effects.

### Plugins
Load plugins to extend server capabilities. Plugins can interface with standard timer events, LED effects, data exporters, and Actions. See [Plugin documentation](https://github.com/RotorHazard/RotorHazard/blob/v3.2.0/doc/Plugins.md) for more information.

### Performance and UX improvements
Faster page load for marshaling, view time elapsed after race clock ends, simpler race stop/save/advance procedures, automatic speech synthesis enabling, manual retries for secondary connections, improved documentation

## Detailed updates from RotorHazard 3.1
* Add last-lap grace period #500 #502 #669 #671
* Two-phase staging (improved start sequence) #646 #665
* Add user-defined event Actions #670
* Add global plugin system #684
    * Load plugins from ./plugins directory
    * Call each [plugin].initialize() to register hooks and event handlers
    * Make LED handlers, data exporters, and Action Effects pluggable
    * Migrate LED handlers and data exporters to plugins
* Add Manual retry for secondary connection #688
* Conditionally announce laps after pilot done #675 #680
* Improve marshaling page load time #390 #666
* Allow stopping race with save+clear #363 #668
* Time counts negative after race end #574 #663
* Add Race Leader announcement #694
* Add "Show late lap" option to Current Race page #695
* Browser clock optimization #683
* Fix arbitrary file read vulnerability #649 #650 #662
* Initialize speech synthesis on page interaction (fixes audio on iOS) #419 #661
* Fix %HEAT% token replacement in manual callout #606 #660 -- Thank you, [andreyzher](https://github.com/andreyzher)
* Extended pause between %PILOTS% %607 #664
* Clarify LED setup (LED_PIN -> LED_GPIO) #667
* Add delete button to callouts #682
* Fix unintended min_lap highlight on Current
* Update frequency reference
* Update LED library for newer hardware
* Update dependency versions #678 #681 #687
* Option to hide RSSI graphing from Run UI #689 
* Fix frontend load issue
* Set gitignore appropriately for plugins
* Update documentation
* Improve staging labeling and documentation #690 
* Bug fixes and stability improvements

<a name="documentation"></a>
## Documentation
Documentation for RotorHazard 3.2.0 may be found at:
https://github.com/RotorHazard/RotorHazard/tree/v3.2.0/doc

## Installation / Upgrade Notes
To install RotorHazard on a new system, see the instructions in '[doc/Software Setup.md](https://github.com/RotorHazard/RotorHazard/blob/v3.2.0/doc/Software%20Setup.md)'

To update an existing RotorHazard installation to this version:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/v3.2.0 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-3.2.0 RotorHazard
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