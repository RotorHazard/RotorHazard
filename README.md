![RotorHazard Logo](/src/server/static/image/RotorHazard%20Logo.svg)

# RotorHazard
FPV Race Timing and Event Management

A multi-node radio frequency race timing system for FPV drone racing, with event management. Uses 5.8GHz video signals broadcast by drones to trigger lap times. Each node listens on a specified frequency and communicates times to a central server (raspberry pi). The server manages a front-end interface, which any device on the same network can connect to via web browser.

RotorHazard builds on the [Delta5 Race Timer](https://github.com/scottgchin/delta5_race_timer), and supports up to 8 nodes.

## Major Features
* Timing and event management on local server hardware
* Modern, mobile-friendly, and responsive
* Confidently calibrate in seconds with visual interface
* Fix calibration issues retroactively after race is complete
* Never miss a lap; recover laps with full accuracy by reviewing RSSI history
* Improved filtering works both indoors and outdoors without adjustment, even in difficult multipathing environments
* Improved synchronization and timing accuracy
* Manage pilots, heats, classes, and race formats
* Full manual control of results for race organizer
* Statistics broken out by event, class, heat, and round
* Sends realtime lap data to livetime
* LED and audio support to indicate race staging, starts, and other events
* JSON API to retrieve timing data from other systems

## Hardware and Software Setup
To build and configure the system, follow the instructions here:  
[doc/Hardware Setup.md](doc/Hardware%20Setup.md)  
[doc/Software Setup.md](doc/Software%20Setup.md)

## User Guide
For initial setup and running races, follow these instructions: [doc/User Guide.md](doc/User%20Guide.md)

## Migrating from/to Delta5
RotorHazard uses the same hardware, but different code for the nodes. Re-flash your Arduinos as in the [setup instructions](doc/Software%20Setup.md#receiver-nodes-arduinos) whenever you switch between the two projects.

## Contributors
* Michael Niggel
* Eric Thomas
* Klaus Michael Schneider
* Mark Hale
* Cerberus Velvet
* Scott Chin and other [Delta5](https://github.com/scottgchin/delta5_race_timer) Contributors

### Supported by:
[![Propwashed Logo](doc/img/Propwashed-Logo-200w.png)](https://propwashed.com)

### Translators
* Dutch: Kenny Van Der Sypt
* German: Klaus Michael Schneider
* Spanish: Ramon Hernandez Roldan
* French: Yannick M.

## Feedback

Discuss RotorHazard on Facebook:  https://www.facebook.com/groups/rotorhazard

To report bugs or request features, please post a GitHub issue [here](https://github.com/RotorHazard/RotorHazard/issues).

Community contributions are welcome and encouraged; see the [Development.md](doc/Development.md) doc for more info.
