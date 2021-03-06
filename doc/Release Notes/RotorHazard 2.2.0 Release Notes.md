# RotorHazard 2.2.0 Release Notes

RotorHazard 2.2.0 provides many new features and fixes, including:

### Logging
The RotorHazard interface now has a "View Server Log" menu item (in the "..." menu) and a "Download Logs" button that will create and download a '.zip' archive file containing all available log files and the current configuration and database files. When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended.

### VRx Control
See doc/Video Receiver.md

### Streaming
The _..._ -> _Stream Displays_ menu option generates a list of URLs which can be directly placed by OBS into scenes.

### Heat Generation
From _Settings_ -> _Heats_ panel. If an input class other than "Randomize" is selected, heats are generated using the "Win Condition" setting of the input class' race format. Lower seeded heats are added first.

### Display Result Source
Mouse over or click/tap on fastest lap or fastest consecutive time to view which round/heat was the source for that time.

## Updates from RotorHazard 2.1.1

* VRx Control and OSD messaging (supports ClearView 2.0) #291 #285 #236 
* Dynamic overlay pages for use with live streaming (OBS) #318 #282 #226
* Improved results generation performance and caching #293 #193 #113
* Heat generation from class results or available pilots #304 #192
* Pilot sorting by name or callsign #297 #195 #177
* Enable removing of unused pilots, heats, classes #300 #8
* Duplicate heats and classes #314 #180
* New options for staging tones #268 #93 #189
* Display source heat/round for result in summary leaderboard #298 #157
* Highlight laps recorded after fixed-time race ends #209 #313
* Arbitrary user text-to-speech callouts #315 #208 #161
* Hardware power saving #311
* Node hardware addressing update #277 #252 
* Enabling in-system programming of nodes #277 #262
* Improved logging and log visibility #330 #324 #289 #283 #295 #301 #303
* Logs saved to file #323
* Automatic log file pruning #323
* Improved database recovery #308
* Internal event system for triggering behaviors; enables plugins and other 3rd party integrations #273 #299
* Fixed pass crossing issues with maxLapsWin races #348
* Node code simplification and cleanup #296
* Node history buffering #230
* Documentation main page #327 
* Experimental node low-pass filter #230
* Code structure improvements #319 #287 #310 
* Database organization improvements #267 #136 
* Bug fixes #312 #305
* Fixed heat generator update on class renaming #332
* Fixed freqs callout wrong frequencies #336
* Fixed IMDtabler reads unused nodes #335
* Added documentation on [logging configuration](https://github.com/RotorHazard/RotorHazard/blob/main/doc/Software%20Setup.md#logging)
* Added Release Notes files in doc
* Other documentation updates

## Upgrade Notes

To install RotorHazard on a new system, see the instructions in doc/Software Setup.md

To update an existing RotorHazard installation to this version:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/2.2.0 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-2.2.0 RotorHazard
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
There are node code changes for this version (since 2.1.1) to enable hardware power saving, history buffering, new hardware addressing spec, in-system programming, and other features. Please upgrade using the code supplied with this release.
