# Secondary / Split Timers

Additional RotorHazard timers may be attached as "secondary" units (as a cluster), interfaced via their network connection (i.e., WiFi).  The default mode is 'split' (for split timing), which allows multiple timers to be placed around the track to get intermediate lap times.  A 'mirror' mode is supported, in which the secondary timer will mirror the actions of the primary (for instance as an "LED-only" timer that displays the actions of the primary), and also an 'action' mode (see [below](#action-mode)).

## Secondary Configuration

On the secondary timer, no configuration changes are needed. It may be necessary to log in to the web interface on the secondary timer and perform tuning adjustments.

## Primary Configuration

Additional timer connections may be configured from the `Settings` page. Open the `Secondary Timers` panel to begin. After modifying any parameters for Secondaries, a restart is required to apply the changes.

On the primary timer, add a new connection by typing its address into the `Address` field under the `New Secondary` heading. Upon completing entry, (tab key or click elsewhere to de-select,) a new `Secondary` section will be created. You may add multiple secondary connections in the same way.

After the `Secondary` section is created, you may add parameters to modify their behavior. Open the `New Key` dropdown and select an item. It will be immediately added to the parameter list below alongside an input where you can modify the value for the key.

### Required parameters
* `Address`: The IP address or hostname and optional port for the secondary timer. For example, `rhmirror.local` or `192.168.1.2:5000`
* `Mode`: The mode for the timer: "split", "mirror", or "action"

Clearing the `Address` field will remove the configuration for this Secondary completely.

### Optional parameters

* `Callout`:  Which value to be announced: time, speed, both time and speed, name, or none
* `Distance`: The distance from the previous timer, which is used to calculate speed (see below)
* `Query Interval`: Number of seconds between heartbeat/query messages (default 10)
* `Receives Events`: Set 'true' to propagate timer events from primary (default 'false' for "split" timer, 'true' for "mirror" timer)
* `Timeout (seconds)`: Maximum number of seconds to wait for connection to be established (default 300)

To enable the announcement of split times, see the "*Secondary/Split Timer*" option on the *Settings* page in the *Audio Control* section. To enable audio indicators of when a secondary timer connects and disconnects, select the "*Secondary Timer Connect / Disconnect*" checkbox under "*Indicator Beeps*". (Note that these options will only be visible if a secondary timer is configured.)

The type of value that is announced (time vs. speed) may be adjusted using the `Callout` item.

To configure a secondary timer to announce speed values, set the `Distance` item to a value representing the distance from the previous split timer (or the primary timer). This value will be divided by the number of seconds elapsed since the pass on the previous timer. To have the speed units be announced in miles per hour, measure the distance in feet, divide it by 1.466 and set that as the "distance" value. For instance, if the timers are separated by 100 feet, set the "distance" value to 68.21 (for callouts in MPH). For metric values, setting the "distance" item to the number of meters * 3.6 should result in KM/H values.

The "address" value may be specified using asterisk-wildcard characters. For instance, if the IP address of the 'primary' timer is "192.168.0.11":  `"*.77" => "192.168.0.77"`, `"*.*.3.77" => "192.168.3.77"`, `"*" => "192.168.0.11"`

A secondary timer may also be configured to play a tone, and to trigger events, for example:

* `Mode`: Split
* `Event`: Split time Pass
* `Effect`: Speak
* `Text`: %PILOT% split time is %SPLIT_TIME%
* `Tone Duration`: 50
* `Tone Frequency`: 400
* `Tone Volume`: 100
* `Tone Type`: Square

The name specified by the `Event` parameter will appear as an item in the 'Event Actions' section on the 'Settings' page in the RotorHazard web GUI. If a matching event/action does not already exist then it will be created and populated with the values specified by the (optional) `Effect` and `Text` parameters (these values may be modified in the RotorHazard web GUI).

* `Event`: The name of the event/action to be triggered
* `Effect`: "Speak" (the default), "Message", "Alert", or "None" (to have no action associated with the event)
* `Text`: The text value for the effect (it may include substitution values like "%PILOT%")

See the '[Event Actions](../doc/User%20Guide.md#event-actions)' section in the [User Guide](../doc/User%20Guide.md) for the list of substitution values that may be specified.

A tone may be configured to be played after each lap pass on the secondary timer:
* `Tone Duration`: The length of the tone, in milliseconds (or 0 for no tone, the default)
* `Tone Frequency`: The frequency of the tone, in hertz (or 0 for no tone, the default)
* `Tone Volume`: The volume of the tone, from 0 to 100 (the default is 100)
* `Tone Type`: The sound type of the tone, one of: "Square" (the default), "Sine", "Sawtooth", or "Triangle"


### Action Mode

A secondary timer may be configured to operate in 'action' mode, where each lap pass on the timer triggers an event (and a configurable action/effect).

The event/effect/text and "tone..." options described above may also be configured for action-mode timers.

* `Minimum Repeat (secs)`: The minimum number of seconds allowed between repeated triggerings of the event/action

<br/>

### Notes

For best results, the primary and secondary timers should be running the same version of the RotorHazard server.

Missed/incorrect split times will have no impact on the recording of lap times by the primary timer.

The status of connected secondary timers may be viewed on the *Settings* page in the *Status* section. (This status information is also available on the *Run* page.) The following items are displayed:
 * *Address* - Network address for the secondary timer (click to bring up the web-GUI for the timer)
 * *Type* - After the address will be an 'S' if split timer, an 'M' if mirror timer, or an 'A' if action timer
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

<br/>

## Clock Synchronization

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

## Wi-Fi based cluster

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

### Random number generator

The random number generator helps improve WiFi connectivity (maintains entropy for encryption). Activate hardware RNG to improve available entropy.

	sudo apt-get install rng-tools

Edit /etc/default/rng-tools and uncomment the line:

    HRNGDEVICE=/dev/hwrng

Then, restart rng-tools with

    sudo service rng-tools restart

<br/>

-----------------------------

See Also:  
[doc/Software Setup.md](Software%20Setup.md)  
[doc/User Guide.md](User%20Guide.md)
