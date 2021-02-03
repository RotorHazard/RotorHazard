![RotorHazard Logo](/src/server/static/image/RotorHazard%20Logo.svg)

[![CI](https://api.travis-ci.com/RotorHazard/RotorHazard.svg)](https://travis-ci.com/RotorHazard/RotorHazard)

# RotorHazard
FPV Race Timing and Event Management

A multi-node radio frequency race timing system for FPV drone racing, with event management. Uses 5.8GHz video signals broadcast by drones to trigger lap times. Each node listens on a specified frequency and communicates times to a central server (raspberry pi). The server manages a front-end interface, which any device on the same network can connect to via web browser.

RotorHazard builds on the [Delta5 Race Timer](https://github.com/scottgchin/delta5_race_timer), and supports up to 8 nodes.

## Major Features
* Race timing and event management on local hardware, no internet connection needed
* Full screen and mobile-friendly responsive interface
* Confidently calibrate in seconds using visual interface
* Adjust and apply calibration retroactively after race is complete
* Learns which calibration values work for each pilot and automatically applies them to new races
* Never miss a lap; recover laps with full accuracy by reviewing race history
* Advanced signal filtering allows accurate reading both indoors and outdoors, even in difficult multipathing environments
* Accurately tracks analog and DJI HD video transmitters
* Manage pilots, heats, classes, and race formats
* Statistics broken out by event, class, heat, and round
* Generates overlay displays and results pages for use with live streaming software such as OBS
* Timer hardware synchronized with user interface for accurate start/end signals with compensation for poor network connectivity
* LED and audio support to indicate race staging, starts, and other events
* Sends live updates of lap times and split times to pilot OSD
* Control connected video receivers; change frequency and view lock status
* Connect other systems to extend functionality via MQTT or JSON API
* Sends realtime lap data to LiveTime

## Documentation
For instructions on how to build and operate the current version of RotorHazard, follow the [Documentation](https://github.com/RotorHazard/RotorHazard/releases/latest#documentation) link on the [lastest-release page](https://github.com/RotorHazard/RotorHazard/releases/latest).

An easy-to-build single node version of RotorHazard may also be constructed -- see [doc/USB Nodes.md](doc/USB%20Nodes.md) for more info.

**Note:** The 'master' branch in the GitHub repository will usually contain the latest development code, which may not be stable. To install or upgrade to the latest stable release, please follow the [Documentation](https://github.com/RotorHazard/RotorHazard/releases/latest#documentation) link on the [lastest-release page](https://github.com/RotorHazard/RotorHazard/releases/latest) (see "Software Setup Instructions").

## Migrating from/to Delta5
RotorHazard uses the same hardware, but different code for the nodes. Re-flash your Arduinos as in the [setup instructions](doc/Software%20Setup.md#rotorhazard-node-code) whenever you switch between the two projects.

## Additional Resources
Links to external resources are available from the [Wiki](https://github.com/RotorHazard/RotorHazard/wiki), including extended tutorials, video content, and a Raspberry Pi setup/install/upgrade/node flashing tool.

## Contributors
* Michael Niggel
* Eric Thomas
* Mark Hale

With support from Ryan Friedman, Klaus Michael Schneider, Cerberus Velvet, David Just, Paweł Fabiszewski, Diez Roggisch, Roger Bess, Kęstutis Strimaitis, Scott Chin, and other [Delta5](https://github.com/scottgchin/delta5_race_timer) Contributors

### Supported by:
[![Propwashed Logo](doc/img/Propwashed-Logo-200w.png)](https://propwashed.com)

### Translators
* Dutch: Kenny Van Der Sypt
* German: Klaus Michael Schneider, Christian Baumgartner
* Spanish: Ramon Hernandez Roldan
* French: Yannick M.
* Polish: Mariusz Misiurek and Paweł Fabiszewski

## Feedback

Discuss RotorHazard on Facebook:  https://www.facebook.com/groups/rotorhazard

To report bugs or request features, please post a GitHub issue [here](https://github.com/RotorHazard/RotorHazard/issues). When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended (see [here](doc/Software%20Setup.md#logging) for more information on logging).

Community contributions are welcome and encouraged; see the [Development.md](doc/Development.md) doc for more info.
