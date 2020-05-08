# Video Receiver

RotorHazard supports wireless communications with video receivers. Initial support is released for the ClearView2.0 receiver. The following capabalities are added with this functionality:

* Race Manager can change frequencies of timer node and video receivers at the same time to avoid frequency conflicts
* Race Manager can view if video receivers are locked onto a video signal
* Pilots can see race start and finish messages on their video receiver's OSD
* Pilots can see lap times and splits on their video receiver's OSD

**TODO**: Insert demo video

## Software Setup in RotorHazard

1. In your server config file, edit VRX_SERVER "ENABLED" to true
   
   * 
	```json
		"VRX_SERVER": {
				"HOST": "localhost",
				"ENABLED": true
			},	
	```	
   * The default config file is located at `RotorHazard/src/server/config.json`,
1. Install the ClearView Receviers  
   * `cd ~`
   * `git clone https://github.com/ryaniftron/clearview_interface_public.git --depth 1`
   * `cd ~/clearview_interface_public/src/clearview-py`
   * `python2 -m pip install -e .`

## ClearView2.0 Receivers

Required Hardware:
* ClearView 2.0
* ESP32 Dongle

### Update Software

* Update to the latest firmware on the CV2.0 from the [update server](https://github.com/ryaniftron/clearview_interface_public#useful-links)
* Update your ESP32 with the **TODO** OTA method

### Test It

1. Test ESP32 communication with CV2.0

   * **TODO**

1. Test joining a WiFi network

   * **TODO**	

1. Test communication with the RH network

   * **TODO**
