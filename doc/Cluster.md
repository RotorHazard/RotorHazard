# Cluster

Additional RotorHazard timers may be attached as "slave" units, interfaced via their network connection (i.e., WiFi).  The default mode is 'timer' (for split timing), which allows multiple timers to be placed around the track to get intermediate lap times.  A 'mirror' mode is also supported, in which the slave timer will mirror the actions of the master (for instance as an "LED-only" timer that displays the actions of the master).

### Configuration

Additional timers may be configured (in 'src/server/config.json') under "GENERAL" with a "SLAVES" entry containing an array of IP addresses of the slave timers in track order.

```
{
	"GENERAL": {
		... ,
		"SLAVES": ["192.168.1.2:5000", "192.168.1.3:5000"]
	}
}
```

Additional options may be configured, for example:

```
{
	"GENERAL": {
		... ,
		"SLAVES": [{"address": "192.168.1.2:5000", "mode": "timer", "distance": 5}, {"address": "192.168.1.2:5000", "mode": "mirror"}],
		"SLAVE_TIMEOUT": 10
	}
}
```
* "address": The IP address and port for the slave timer.
* "mode": The mode for the timer (either "timer" or "mirror").
* "distance": The distance from the previous gate (used to calculate speed).
* "SLAVE_TIMEOUT": Maximum number of seconds to wait for connection to be established.

### Clock Synchronization

The accuracy of reported split times will be higher if all timers have their clocks synchronized. Adding precision [real-time clock (RTC) devices](Real%20Time%20Clock.md) like the [DS3231](https://www.adafruit.com/product/3013) to all the timers can accomplish this, or NTP can be configured to operate between the timers as shown below.

On all timers:

	sudo apt-get install ntp

On the master, edit /etc/npd.conf and add lines similar to:

	restrict 192.168.123.0 mask 255.255.255.0
	broadcast 192.168.123.255
	
On the slaves, edit /etc/npd.conf and add lines similar to:

	server 192.168.123.1

On all timers:

	sudo systemctl stop systemd-timesyncd
	sudo systemctl disable systemd-timesyncd
	sudo ​/etc/init.d/ntp restart

### Random number generator

The random number generator helps improve WiFi connectivity (maintains entropy for encryption). Activate hardware RNG to improve available entropy.

	sudo apt-get install rng-tools

Edit /etc/default/rng-tools and uncomment the line:

    HRNGDEVICE=/dev/hwrng

Then, restart rng-tools with

    sudo service rng-tools restart

### Notes

Missed/incorrect split times will have no impact on the recording of lap times by the master timer.

The status of connected slave timers may be viewed on the *Settings* page in the *System* section. Clicking on the slave-timer address will bring up the web-GUI for the timer. The "*Seconds since last contact*" value should always be less than 20 (higher values indicate network communications problems).

To enable the announcement of split times, see the "*Split Times*" option on the *Settings* page in the *Audio Control* section. (Note that this option will only be visible if a slave timer is connected.)

Doing normal operation, lap history-data will not be saved on the slave timer(s). To view lap history-data and perform marshaling on a slave timer, hit the '*Save Laps*' button on the slave timer before the race is saved or discarded on the master, and then go to the *Marshal* page on the slave timer.

A slave can also be a master, but sub-splits are not propagated upwards.

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
