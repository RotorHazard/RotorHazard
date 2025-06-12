![RotorHazard Logo](/src/server/static/image/RotorHazard%20Logo.svg)

# RotorHazard
**FPV Race Timing and Event Management**

Tracks 5.8GHz (video) signals broadcast by FPV racing drones and uses them for lap timing. Video receiver hardware listens on specified frequencies and communicates to a central server (usually a Raspberry pi). The server offers race organizer management, pilot/spectator information and results, is accessed with a web browser, and communicates with external systems. Supports up to 16 simultaneous racers.

> [!TIP]
>Join a community to discuss RotorHazard: [Discord](https://discord.gg/ANKd2pzBKH) | [Facebook](https://www.facebook.com/groups/rotorhazard)
>
> Sponsor RtorHazard's development:[GitHub](https://github.com/sponsors/HazardCreative) | [Patreon](https://www.patreon.com/rotorhazard)


## Features
* Self-contained on local hardware, no internet connection needed
* Server synchronized with user interface for accurate start/end signals; compensates for poor network connectivity
* Connect other systems and extend functionality via [plugins](doc/Plugins.md)
* Server runs on any device supporting Python

### Timing
* Verified accuracy by independent 3rd party testing
* **Never miss a lap**; Recover laps with full accuracy by reviewing race history (marshaling)
* Accurately tracks analog and digital (HD) video transmitters
* Simple visual system calibration before or after a race has completed
* Learns which calibration values work for each pilot and automatically applies them to new races (adaptive calibration)
* Advanced signal filtering allows accurate reading both indoors and outdoors, even in difficult multipathing environments

### Event Management
* Run events with hundreds of pilots and race heats
* Manage pilots, heats, classes, and race formats before or after races are run
* Supports common event/race formats and ranking structures; extensible by plugin
* Statistics broken out by event, class, heat, and round
* Generates overlay displays and results pages for use with live streaming software such as OBS
* LED and audio support indicate race staging, starts, lap times, and other events
* Send live updates of lap times and split times to external systems such as pilot OSD

<br />

## Getting Started

RotorHazard consists of three primary components: Timing hardware, server, and frontend interface. **Most users will begin with RotorHazard by building or buying timing hardware and then installing the server software on it.**

> [!IMPORTANT]
> Live documentation may contain information that does not apply to the current release. For documentation relating to the *current stable version only*, follow the [Documentation](https://github.com/RotorHazard/RotorHazard/releases/latest#documentation) link on the [latest-release page](https://github.com/RotorHazard/RotorHazard/releases/latest).

### Timing Hardware

RotorHazard makes use of a collection of RX5808 video receiver modules. Receivers are tuned to active FPV race channels and monitor their signal strength. A small but dedicated processor (Arduino or STM32) is used to monitor the modules and communicate with the server. Timer builds generally include hardware to run the server as well, making a self-contained unit.

- Choose a style from the available [Build Resources](resources/README.md). Build styles include circuit boards, BOM, and 3D-printable cases.
- [Delta5 Race Timer](https://github.com/scottgchin/delta5_race_timer) hardware is still supported and runs with full accuracy. Replace the Delta5 server software using the current RotorHazard server [setup instructions](doc/Software%20Setup.md), ensuring that you complete a [re-flash of the Arduinos](doc/Software%20Setup.md#rotorhazard-node-code).

### Server

The RotorHazard server aggregates timing signals, handles event structure, calculates results, provides the management interface, and communicates with external timers and systems. It can be run on most systems where Python can be installed, but the recommended and best supported installation is to a **Raspberry Pi**.

> [!NOTE]
> The [RotorHazard Install Manager](https://github.com/RotorHazard/RH_Install-Manager) can greatly simplify installation. Once you have installed the operating system to your SD card, download and run the Install Manager.

> [!IMPORTANT]
> The 'main' branch in the GitHub repository will usually contain the latest development code, which may not be stable. To install or upgrade to the latest stable release, please visit the [latest-release page](https://github.com/RotorHazard/RotorHazard/releases/latest).

### Frontend (Event Management) Interface

The frontend interface is used for event management and viewing results. The server can be accessed by any device (laptop, phone, tablet) with a modern web browser (Firefox, Chrome, Safari) on any operating system (Windows, MacOS, Android, iOS).

- Once the server is running, connect to the server's address using standard IP-based networking.
- All event management is done through the interface.
- No dedicated software or app is necessary to access the interface.

<br />

## Additional Resources

RotorHazard's features and functionality can be greatly extended beyond the core system.

### Plugins

Plugins allow 3rd parties to develop code which runs on the RotorHazard server.
- "Community Plugins" may be found within RotorHazard's interface. From here, plugins are easily downloaded, installed, and upgraded.
- See [Plugins](doc/Plugins.md) for information on manual installation.
- Individual plugins may have specific setup requirements. Read each plugin's documentation before use.

### Wiki

Many additional resources are available from the [Wiki](https://github.com/RotorHazard/RotorHazard/wiki), including extended tutorials, build tools, SD card images, and video content. Browsing these resources is strongly recommended for new users.

<br />

## Feedback

To report bugs or request features, please [post a GitHub issue](https://github.com/RotorHazard/RotorHazard/issues). When reporting issues, use the "Download Logs" button and include the generated '.zip' file.

Community contributions are welcome and encouraged; see [Development](doc/Development.md) for more information.
