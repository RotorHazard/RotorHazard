![RotorHazard Logo](/src/server/static/image/RotorHazard%20Logo.svg)

# RotorHazard
FPV Race Timing and Event Management

A multi-node radio frequency race timing system for FPV drone racing, with event management. Uses 5.8GHz video signals broadcast by drones to trigger lap times. Each node listens on a specified frequency and communicates times to a central server (raspberry pi). The server manages a front-end interface, which any device on the same network can connect to via web browser.

RotorHazard builds on the [Delta5 Race Timer](https://github.com/scottgchin/delta5_race_timer), and supports up to 8 nodes.

## Major Features
* Timing and event management on the same hardware
* Modern, mobile-firendly, and highly responsive user interface
* Manage pilots, heats, race classes, race formats, and tuning profiles
* LED and audio support to indicate race staging, starts, and other events
* Real-time statistics and race history
* Fine control of filtering and calibration allows indoor and outdoor use, even in difficult multipathing environments
* Supports all frequencies in the 5.8GHz band

## Hardware and Software Setup
To build the system, follow the instructions here: [/doc/Hardware and Software Setup Instructions.md](/doc/Hardware%20and%20Software%20Setup%20Instructions.md)

## User Guide
For initial setup and running races, follow these instructions: [/doc/User Guide.md](/doc/User%20Guide.md)

## Migrating from/to Delta5
RotorHazard uses the same hardware, but different code for the nodes. Re-flash your Arduinos as in the [setup instructions](/doc/Hardware%20and%20Software%20Setup%20Instructions.md#receiver-nodes-arduinos) whenever you switch between the two projects.

## Contributors
* Michael Niggel
* Eric Thomas
* Scott Chin and other [Delta5](https://github.com/scottgchin/delta5_race_timer) Contributors

### Supported by:
[![Propwashed Logo](/doc/img/Propwashed-Logo-200w.png)](https://propwashed.com)


Community contributions are welcome and encouraged.

Submit an [issue](https://github.com/RotorHazard/RotorHazard/issues) or [pull request](https://github.com/RotorHazard/RotorHazard/pulls), or discuss the project on [Facebook](https://www.facebook.com/groups/749387998753163/).
