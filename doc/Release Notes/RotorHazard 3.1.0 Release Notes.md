# RotorHazard 3.1.0 Release Notes

## New features and important fixes

### Major refactoring of internal data structures
Cleanup of existing code, including older poorly-written functions. Performance improved by 60% in critical processing areas.

### Improved and expanded public display of information
"Event" page now better describes participants, heat setup, classes, and other event parameters. [Markdown](https://www.markdownguide.org/) may now be used in event and class descriptions for richer, better formatted text when viewed by event participants. Users can define time format strings for better internationalization. Current race and streaming overlays display cached race data when appropriate.

### Expanded LED options
LED panel effects: (lap count, race position, lap time, staging countdown, lap count grid, local RSSI graphing), per-pilot color selection, per-frequency color selection (BetaFlight standard), LED idle states

### Improved user interface
Crossing events now represented in real-time graphs, touch/drag support for setting enter/exit values, new highlight for "late" laps (2nd+ crossing after time expires)

### Improved usability
Recalculate race winner after lap deleted, reversed lap order display option, allow full access is admin fields are empty

Note: Timers using S32_BPill / STM32-based boards should upgrade to this version of RotorHazard, as it fixes an issue ("HTTP Error 406") that occurs when using the 'Update Nodes' feature.

## Detailed updates from RotorHazard 3.0

* Major refactoring of internal data structures #509 #528 #531 #534
* Add Markdown support for event and class descriptions #519
* Display heats by class #521
* Display race starts statistic #522
* Improve and expand public display of Event information #523
* User-defined time formatting #520
* Add graphical crossing indicators #533
* Text effects for LED panels #541
* Local RSSI graph for LED panels #567
* Per-pilot and per-frequency color selection #149 #545
* Add LED idle states #239 #546
* Improve display of "current race" (Current page, stream overlays) with recent race cache
* Improve LED effects and handling #582 #588 
* Enable additional LED effects while using Mirror (Secondary) timers #582
* Save race when requested even if no lap data exists #597
* Save race data on split timer #603
* Improvements to cluster timer reconnects
* Clarify intent with %FREQS% #604
* Fixed issue with adaptive calibration
* Fixed issue with race/pilot reassignments
* Fixed issues with lap source display
* Fixed issue with stream display
* Fixed issue with event results display #599
* Fixed database loading/restore issues #600
* Fixed issue with shutdown LED effects #589
* Show warning if Python 2 version
* Fixed I2C bus issue with RPi 4 and latest OS
* Fixed HTTP Error 406 when updating S32_BPill nodes
* Improved handling S32_BPill board with no modules installed
* Added log of slot positions for S32_BPill rec modules
* Fixed winner not cleared after save/discard
* Volume=zero now fully mutes
* Improve handling gate crossings at race stop #611
* Stop announcing lap numbers after winning laps #612
* Recalculate race winner after lap deleted on Run page #613
* Added 'Lap order reversed' display setting #617
* Added database view command-line args #623
* Allow full access if admin fields are empty
* Various minor fixes and improvements


<a name="documentation"></a>
## Documentation
Documentation for RotorHazard 3.1.0 may be found at:
https://github.com/RotorHazard/RotorHazard/tree/3.1.0/doc

## Installation / Upgrade Notes
To install RotorHazard on a new system, see the instructions in '[doc/Software Setup.md](https://github.com/RotorHazard/RotorHazard/blob/3.1.0/doc/Software%20Setup.md)'

To update an existing RotorHazard installation to this version:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/3.1.0 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-3.1.0 RotorHazard
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