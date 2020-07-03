# RotorHazard 2.1.0 Release Notes

## Updates from 2.0

 * Improved browser/pi time sync (improves sync of audio/LED start signals and time capture)
 * Adjust calibration based on pilot/node history
 * Touch-marshaling: click and drag on graph to quickly select laps and adjust tuning parameters
 * Auto-increment heat when race is saved (maintains same class)
 * LED effects library
 * LED management maps effects to timer events
 * LED panel support: image bitmap display, image rotation, row index conversion
 * Colorblind- and FPV-camera-friendly images for 16x16 LED panels
 * Improved responsiveness (non-blocking pass callbacks and results calculations)
 * Improved documentation; especially tuning parameters with new illustrations
 * Offline documentation reader
 * Improved UI for race marshaling (graph scaling, data reload, default to most recently run race)
 * New heat pilot assignments default to "None"
 * Hide disabled nodes from UI (when disabled by frequency)
 * Keep deleted realtime laps for restoration in marshaling
 * Frontend display of lap number, time since start, time since lap 0 (Klaus-Michael PR #105)
 * Highlight laps recorded after time has expired during a fixed-time race
 * Generic sensor framework (pulquero PR #159)
 * Support for USB-connected nodes (see 'doc/USB Nodes.md')
 * Cleaned-up and improved node code (pulquero PR #99)
 * Added node I2C comms monitor (should prevent unresponsive nodes)
 * Improved node status LED: now shows idle (2s blink), crossing (solid), and data bus activity
 * Split-timing support (experimental) (pulquero PR #94)
 * Band scanner (experimental, enabled via Debug config flag) (pulquero)
 * Browser sync quality now visible under ... -> About RotorHazard (Run or Current page only)
 * Added server reboot button
 * Various bug fixes and minor improvements
 * Added primary documentation translations (es, pl)
 * Added Polish language
 * Language updates
 * Dependency updates

### LED Panel

LED panel hardware is configured exactly like LED strips. To enable image display, follow the instructions at the top of src/server/led_handler_bitmap.py to install necessary libraries. See config-dist.json for new LED options that may be used. If your panel image requires rotation, use `PANEL_ROTATE` with the number of 90-degree CCW rotations needed [0..3]. Some panels are not wired in a typical left-to-right pattern and are instead wired in a Z-pattern (every other row is addressed right-to-left). Set `"INVERTED_PANEL_ROWS": true` to correct this.

### Upgrade Notes

To install RotorHazard on a new system, see the instructions in doc/Software Setup.md

To update an existing RotorHazard installation to this version:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/2.1.0 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-2.1.0 RotorHazard
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

### Node Code (Arduino)

Node code changes for NODE_API_LEVEL 22 provide faster node polling and more robust operation (with recovery via a communications monitor). Please upgrade using the code supplied with this release. This version is not different from 2.1.0-beta.2, no updates are needed if upgrading from that version or later.

As always, to report bugs please post a GitHub issue [here](https://github.com/RotorHazard/RotorHazard/issues).
