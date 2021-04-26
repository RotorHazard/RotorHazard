![RotorHazard Logo](/src/server/static/image/RotorHazard%20Logo.svg)

[![CI](https://github.com/pulquero/RotorHazard/actions/workflows/ci.yml/badge.svg)
[![Coverage](https://codecov.io/github/pulquero/RotorHazard/coverage.svg?branch=BetaHazard)](https://codecov.io/gh/pulquero/RotorHazard/)

# BetaHazard
**Cutting-edge innovation in FPV Race Timing and Event Management**

A multi-node radio frequency race timing system for FPV drone racing with event management. Uses 5.8GHz video signals broadcast by drones to trigger lap times. Each node listens on a specified frequency and communicates times to a central server (usually a Raspberry pi). The server's front-end interface, which any device on the same network can connect to via web browser, offers race organizer management and pilot/spectator information. RotorHazard supports up to 16 nodes.

## Major Features
* Race timing and event management on local hardware, no internet connection needed
* Full screen and mobile-friendly responsive interface
* Simple, visual system calibration
* Adjust and apply calibration retroactively after race is complete
* Learns which calibration values work for each pilot and automatically applies them to new races (adaptive calibration)
* **Never miss a lap**; Recover laps with full accuracy by reviewing race history
* Advanced signal filtering allows accurate reading both indoors and outdoors, even in difficult multipathing environments
* Accurately tracks analog and DJI HD video transmitters
* Manage pilots, heats, classes, and race formats before or after races are run
* Statistics broken out by event, class, heat, and round
* Generates overlay displays and results pages for use with live streaming software such as OBS
* Timer hardware synchronized with user interface for accurate start/end signals; compensates for poor network connectivity
* LED and audio support to indicate race staging, starts, and other events
* Send live updates of lap times and split times to pilot OSD
* Control connected video receivers; change frequency and view lock status
* Connect other systems to extend functionality via MQTT or JSON API
* Send realtime lap data to LiveTime

## Documentation
For instructions on how to build and operate the current version of RotorHazard, follow the [Documentation](https://github.com/pulquero/BetaHazard/releases/latest#documentation) link on the [lastest-release page](https://github.com/pulquero/BetaHazard/releases/latest).

See the [RotorHazard Build Resources](resources/README.md) page for information on race-timer circuit boards and 3D-printable cases.

An easy-to-build single-node version of RotorHazard may also be constructed; see [doc/USB Nodes.md](doc/USB%20Nodes.md) for more info.

**Note:** The 'main' branch in the GitHub repository will usually contain the latest development code, which may not be stable. To install or upgrade to the latest stable release, please follow the [Documentation](https://github.com/pulquero/BetaHazard/releases/latest#documentation) link on the [lastest-release page](https://github.com/pulquero/BetaHazard/releases/latest) (see "Software Setup Instructions").

## Migrating from Delta5
RotorHazard is compatible with the hardware specifications of the [Delta5 Race Timer](https://github.com/scottgchin/delta5_race_timer). Install the software on  existing hardware per the [setup instructions](doc/Software%20Setup.md), ensuring that you complete a [re-flash of the Arduinos](doc/Software%20Setup.md#rotorhazard-node-code).

## Additional Resources
Links to external resources are available from the [Wiki](https://github.com/pulquero/BetaHazard/wiki), including extended tutorials, complete SD card images, video content, and a Raspberry Pi setup/install/upgrade/node flashing tool. Browsing these resources is strongly recommended for new users.

## Contributors
* Michael Niggel
* Eric Thomas
* Mark Hale

With support from Ryan Friedman, Klaus Michael Schneider, Cerberus Velvet, David Just, Paweł Fabiszewski, Aaron Smith, Diez Roggisch, Roger Bess, Kęstutis Strimaitis, and previous contributors to [Delta5](https://github.com/scottgchin/delta5_race_timer).

### Translators
* Dutch: Kenny Van Der Sypt
* German: Klaus Michael Schneider, Christian Baumgartner
* Spanish: Ramon Hernandez Roldan
* French: Yannick M.
* Polish: Mariusz Misiurek and Paweł Fabiszewski

## Feedback
To report bugs or request features, please post a GitHub issue [here](https://github.com/pulquero/BetaHazard/issues). When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended (see [here](doc/Software%20Setup.md#logging) for more information on logging).

Community contributions are welcome and encouraged; see the [Development.md](doc/Development.md) doc for more info.
