# Cluster

Additional RotorHazard timers may be attached as "secondary" units, interfaced via their network connection (i.e., WiFi).  The default mode is 'split' (for split timing), which allows multiple timers to be placed around the track to get intermediate lap times.  A 'mirror' mode is also supported, in which the secondary timer will mirror the actions of the primary (for instance as an "LED-only" timer that displays the actions of the primary).

### Configuration

An additional timer may be configured (in 'src/server/config.json' on the primary timer) under "GENERAL" with a "SECONDARIES" entry containing the address of the secondary timer; for example:
```
{
	"GENERAL": {
		... ,
		"SECONDARIES": ["192.168.1.2:5000"]
	}
}
```

Multiple secondary timers may be specified as a list of addresses in track order:
```
{
	"GENERAL": {
		... ,
		"SECONDARIES": ["192.168.1.2:5000", "192.168.1.3:5000"]
	}
}
```

Additional options may be configured, for example:
```
{
	"GENERAL": {
		... ,
		"SECONDARIES": [{"address": "192.168.1.2:5000", "mode": "split", "distance": 5}, {"address": "192.168.1.2:5000", "mode": "mirror"}],
		"SECONDARY_TIMEOUT": 10
	}
}
```
* "address": The IP address and port for the secondary timer.
* "mode": The mode for the timer (either "split" or "mirror").
* "distance": The distance from the previous timer (used to calculate speed).
* "queryInterval": Number of seconds between heartbeat/query messages (default 10).
* "recEventsFlag": Set 'true' to propogate timer events from primary (default 'false' for "split" timer, 'true' for "mirror" timer).
* "SECONDARY_TIMEOUT": Maximum number of seconds to wait for connection to be established.

The "address" value may be specified using asterisk-wildcard characters. For instance, if the IP address of the 'primary' timer is "192.168.0.11":  `"*.77" => "192.168.0.77"`, `"*.*.3.77" => "192.168.3.77"`, `"*" => "192.168.0.11"`

On the secondary timer, no configuration changes are needed.

### Clock Synchronization

The accuracy of reported split times will be higher if all timers have their clocks synchronized. Adding precision [real-time clock (RTC) devices](Real%20Time%20Clock.md) like the [DS3231](https://www.adafruit.com/product/3013) to all the timers can accomplish this, or NTP can be configured to operate between the timers as shown below.

On all timers:

	sudo apt-get install ntp

On the primary, edit /etc/npd.conf and add lines similar to:

	restrict 192.168.123.0 mask 255.255.255.0
	broadcast 192.168.123.255
	
On the secondaries, edit /etc/npd.conf and add lines similar to:

	server 192.168.123.1

On all timers:

	sudo systemctl stop systemd-timesyncd
	sudo systemctl disable systemd-timesyncd
	sudo service ntp restart

### Random number generator

The random number generator helps improve WiFi connectivity (maintains entropy for encryption). Activate hardware RNG to improve available entropy.

	sudo apt-get install rng-tools

Edit /etc/default/rng-tools and uncomment the line:

    HRNGDEVICE=/dev/hwrng

Then, restart rng-tools with

    sudo service rng-tools restart

### Notes

For best results, the primary and secondary timers should be running the same version of the RotorHazard server.

Missed/incorrect split times will have no impact on the recording of lap times by the primary timer.

To enable the announcement of split times, see the "*Cluster/Split Timer*" option on the *Settings* page in the *Audio Control* section. To enable audio indicators of when a cluster/secondary timer connects and disconnects, select the "*Cluster Timer Connect / Disconnect*" checkbox under "*Indicator Beeps*". (Note that these options will only be visible if a secondary timer is configured.)

The status of connected secondary timers may be viewed on the *Settings* page in the *Status* section. (This status information is also available on the *Run* page.) The following items are displayed:
 * *Address* - Network address for the secondary timer (click to bring up the web-GUI for the timer)
 * *Type* - After the address will be an 'S' if split timer or an 'M' if mirror timer
 * *Latency: last min avg max* - Network latency (in milliseconds) for heartbeat/query messages
 * *Disconnects* - Number of times the secondary timer has been disconnected
 * *Contacts* - Number of network contacts with the secondary timer
 * *Time Diff* - Time difference (in milliseconds) between system clocks on primary and secondary timer
 * *Up* - Number of seconds the secondary timer has been connected
 * *Down* - Number of seconds the secondary timer has been disconnected
 * *Availability* - Availability rating (as a percentage) for the secondary timer
 * *Last Contact* - Time (in seconds) since last contact with the timer, or a status message

The web-GUI for the secondary timer may be accessed by clicking on the *Address* value on the status display on the primary timer. From there, lap history may be viewed, marshaling performed and settings adjusted.

When a secondary timer operating in 'split' mode establishes a connection (aka joins the cluster), the database on the timer is backed up and then any existing race data are cleared. The filenames on these backups will have the form "autoBkp_database_YYYYMMDD_HHMMSS.db". The number of these "autoBkp" files retained is limited by the DB_AUTOBKP_NUM_KEEP setting (in "config.json" under GENERAL), with the default value of 30.

A secondary can also be a primary, but sub-splits are not propagated upwards.

If you want to use a Wi-Fi based cluster, instructions for setting up an access point (Wi-Fi hotspot) can be found at
<https://www.raspberrypi.org/documentation/configuration/wireless/access-point.md>.
Also, read <https://github.com/mr-canoehead/vpn_client_gateway/wiki/Configuring-the-Pi-as-a-WiFi-Access-Point>
and <https://superuser.com/questions/1263588/strange-issue-with-denyinterfaces-in-access-point-config>.
Specifically, add `denyinterfaces wlan0` to `/etc/dhcpcd.conf` and `sudo nano /etc/network/interfaces.d/wlan0`
to add

```
allow-hotplug wlan0
iface wlan0 inet static
	address 10.2.2.1
	netmask 255.255.255.0
	network 10.2.2.0
	broadcast 10.2.2.255
	post-up systemctl restart hostapd
```
to make dhcpcd play nice with hostapd.
