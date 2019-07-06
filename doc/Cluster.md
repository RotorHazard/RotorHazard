# Cluster

## Setup

It is important that all timers have their clocks synchronized.
You can use NTP to do this.

### NTP

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

Activate hardware RNG to improve available entropy.

	sudo apt-get install rng-tools

Edit /etc/default/rng-tools and uncomment the line:

    HRNGDEVICE=/dev/hwrng

Then, restart rng-tools with

    sudo service rng-tools restart

### Config

In config.json, under "GENERAL", add a "SLAVES" setting with
an array of IP addresses of the slave timers in track order.

```
{
	"GENERAL": {

		"SLAVES": ["192.168.1.2:5000", "192.168.1.3:5000"]

	}

}

```

Start the slave timers, then start the master.

## Notes

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
