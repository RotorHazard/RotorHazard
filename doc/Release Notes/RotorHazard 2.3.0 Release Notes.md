# RotorHazard 2.3.0 Release Notes

RotorHazard 2.3.0 provides many new features and fixes, including:

### Improved Results Generation
This release provides significant performance advantages when saving races and viewing the results page, particularly for large events. Race results are now atomically cached for each race, heat, class, and event. A local page cache is also maintained. These caching systems are updated on an as-needed basis, preventing rebuild of the entire results cache.

### Expanded Win Conditions and First Crossing Behaviors
Win conditions include common race types and new team racing conditions that use average lap times for the entire team. First crossings can now be hole shots, first lap, or staggered starts. See [Race Formats in the User Guide](https://github.com/RotorHazard/RotorHazard/blob/master/doc/User%20Guide.md#race-format) for more details.

### Retroactive Data Manipulation
Organizers may now remove locks on saved race data to manipulate assigned pilots, heats, classes, etc. for the correction of event setup errors in prior races.

### Database Controls and Migrations
Save, restore, and delete database files in the db_bkp folder from the Database panel in Settings. Also restores database files in older formats.

### Split Timing Improvements
Support for multiple cluster/split timers has been fleshed out and improved. See '[doc/Cluster.md](https://github.com/RotorHazard/RotorHazard/blob/master/doc/Cluster.md)' for details.

### Frequency Reference
A [Frequency Reference](https://github.com/RotorHazard/RotorHazard/blob/master/doc/Frequency%20Reference.md) has been added to documentation, and can be pulled up in the offline documentation viewer.

### Python 3 support
Python 2 is past end of life. RotorHazard 2.3.0 may be run on either Python 2 or Python 3. (This is also the last release to support Python 2; after this release, only Python 3 will be supported.)

### Official PCB release
Paweł Fabiszewski has developed a PCB which implements current hardware standards to simplify wiring and component placement, expediting timer builds and improving usability. See [RotorHazard PCB](https://github.com/RotorHazard/RotorHazard/tree/master/resources/PCB) for more details.

### LiveTime Controls
Visit /decoder to open a dedicated page for settings which apply when RotorHazard is connected to LiveTime.

## Updates from RotorHazard 2.2

* Optimize result page rebuild process #446 
* First crossing options (hole shot, first lap, staggered start) #442
* Retroactive data maniplulation #440
* Added PCB files and documentation #397
* Improved results page build and caching #384
* Added expanded win conditions #339 ([See documentation](https://github.com/RotorHazard/RotorHazard/blob/master/doc/User%20Guide.md#race-format))
* Added "decoder" page for LiveTime settings #316
* Added [Frequency Reference](https://github.com/RotorHazard/RotorHazard/blob/master/doc/Frequency%20Reference.md) to documentation
* Split timer improvements #377 #378 #399 #402 #404 #417 #439
* Python 3 compatibility #320 #415 
* Improved display on iOS #470 
* Automatic dark mode #443
* Reconnect when page regains visibility (device wakes from sleep) #447
* Server support of up to 16 nodes (I2C limit is still 8)
* Fix major issue with events and multiple assigned handlers
* Restore and delete databases from UI #59 #421
* Added DJI 50MB channels as "J" band
* Updated DJI 25MB Ch6 to 5880
* Added Shark Byte channels as "S" band
* Added start-of-race enter/exit lowering #389
* Made auto heat increment optional #394
* Added hotkey for start/stop race (spacebar) #437 
* Added more announcement options #395
* Support most recent CVCM protocol #408
* Allow log updates page to be paused #401 #422
* Improved database migrations and fix issues #415
* Enforce format switch on heat change and race staging
* Added semaphore lock for node I/O access #467
* Clears stream node display when seat is empty
* Handle system clock time jumps #439
* Improve message queuing for cluster timers #455
* VRx Control shuts off OSD on CV2.0 #457
* VRx Control uses preliminary JSON protocol #438
* Remove 'null' pilots from results list #388
* Add folder for user data that is not overwritten on update #356 #423
* Ensure correct permissions on generated files and folders
* Improved exception catching/logging on thread/route/render functions #387
* Decoupled sensors from timing interface #386 
* Improved translation support #414 #425
* Additional German translations #414 #425
* Fixed scheduled race cancellation
* Fixed plugin loading #373
* Code refactoring #398 
* Alter last heat's ID to 1 after others deleted #426
* Various minor bug fixes and improvements
* Improved documentation #403

## Upgrade Notes

To install RotorHazard on a new system, see the instructions in '[doc/Software Setup.md](https://github.com/RotorHazard/RotorHazard/blob/master/doc/Software%20Setup.md)'

To update an existing RotorHazard installation to this version:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/2.3.0 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-2.3.0 RotorHazard
rm temp.zip
cp RotorHazard.old/src/server/config.json RotorHazard/src/server/
cp RotorHazard.old/src/server/database.db RotorHazard/src/server/
```
The previous installation ends up in the 'RotorHazard.old' directory, which may be deleted or moved.

The RotorHazard server dependencies should also be updated (be patient, this command may take a few minutes):
```
cd ~/RotorHazard/src/server
sudo pip install --upgrade --no-cache-dir -r requirements.txt
```

## Node Code (Arduino)
There are no node code changes for this version since 2.2.0. You will need to upgrade your Arduino firmware only if upgrading from a version prior to 2.2.

## Issues
If you encounter a bug, please report it using the [Issues page on GitHub](https://github.com/RotorHazard/RotorHazard/issues). Open "View Server Log" (in the "..." menu) and a "Download Logs" button will create and download a '.zip' archive file containing all available log files and the current configuration and database files.
