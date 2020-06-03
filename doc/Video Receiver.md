# Video Receiver Control

_This functionality is still in beta and will continue to evolve._

RotorHazard supports wireless communications with video receivers. Initial support is released for the ClearView2.0 receiver. The following capabalities are added with this functionality:

* Publish lap times and splits to video receiver OSD
* Publish race status messsages (Ready, Go, Stop) to OSD
* Publish other priority messages to OSD
* Synchronize frequencies of connected video receivers
* View whether video receivers are locked onto a signal

_Note: messages are NOT currently synchronized to the race clock._

## OSD Messages

### Race messages
Race status messages are displayed automatically. The messages will change depending on current _Race Format_ settings, particularly _Win Condition_. Race messages generally follow this pattern:
`[Rank]-[Callsign] [Last Lap Number]|[Last Lap Time] / [+/-][Split] [Split Callsign]`
For example:
`1-Hazard L3|0:24.681 / -0:04.117 RYANF55`

* Most race modes: The split displayed is the difference in total race time to the pilot ahead until the next pilot crosses, then updates to the pilot behind.
* Fastest Lap: The split is always the next pilot ahead. If in first place, the split is againt the best course lap.
* Fastest 3 Consecutive: The split is replaced with pilot's current best consecutive 3-lap time.

Long pilot callsigns are truncated for the OSD.

Characters used to prefix the ranking and lap number can be configured in the _VRx Control_ panel in _Settings_.

### Custom Messages
From the _Send Message_ panel on the _Settings_ page, messages marked to _Send to VRx_ will be displayed on all connected Video Receiver OSDs.

## Settings

The status of connected receivers are displayed in the _VRx Control_ panel in _Settings_. Receivers are assigned to a node to follow for video frequency and OSD messages.

**IMPORTANT: Changing the node/seat number in this panel immediately changes the VRx and may cause a pilot to lose video contact. USE WITH DISCRETION.**

Characters used to prefix the rank and lap number in the OSD message can be set here.

## Software Setup in RotorHazard

### Install and configure an MQTT broker.
The MQTT broker does not need to be installed on the same system as the RorotHazard server, though it does simplify setup and maintenance. To install on a Raspberry Pi, from the terminal:
```
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto.service
```

### Add the VRX_CONTROL block to config.json.
Set "ENABLED" to "true" and "HOST" to the IP address of your MQTT broker (use "localhost" if it is on the same system as the RotorHazard server). Example:
```
"VRX_CONTROL": {
    "HOST": "localhost",
    "ENABLED": true
},
```

The default config file is located at `RotorHazard/src/server/config.json`.

### Install the ClearView Recevier Library.
A python library is required to communicate with ClearView devices. Currently the only supported receiver is ClearView2.0, so this install is required.
```
cd ~
git clone https://github.com/ryaniftron/clearview_interface_public.git --depth 1
cd ~/clearview_interface_public/src/clearview-py
python -m pip install -e .
```

## Set up ClearView2.0 Receivers

Be sure your ClearView2.0 Receiver is [updated to the latest version](http://proteanpaper.com/fwupdate.cgi?comp=iftrontech&manu=2).

A ClearView Comms Module allows the ClearView2.0 to recieve commands from a network. The CVCM will be made commercially available. Users may build a CVCM with an ESP32 development board and a CV2 update board. Visit the [ClearView Interface](https://github.com/ryaniftron/clearview_interface_public) code repo for more information and build instructions.
