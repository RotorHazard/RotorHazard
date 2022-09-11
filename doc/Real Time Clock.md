# Real Time Clock

The standard Raspberry Pi does not feature a real-time clock (RTC) -- when it has an internet connection the Pi will fetch the current date and time from an online server, but if an internet connection is not available when the Pi starts up, its date/time will be wrong.  (It will usually revert to the last date/time it was using, and go from there.)

Adding a real-time clock module addresses this problem.  The [DS3231](https://www.adafruit.com/product/3013) module is recommended, as it keeps very accurate time.  There are other, cheaper modules that will also do the job (albeit with less precision), such as the [PCF8523](https://www.adafruit.com/product/3295) and [DS1307](https://www.adafruit.com/product/3296).

The RTC module uses an onboard coin-cell battery ([CR1220](https://www.adafruit.com/product/380)), which allows it to keep track of time while the system is powered off.

### Wiring

If you're using an [S32_BPill PCB &#10132;&#xFE0E;](https://github.com/RotorHazard/RotorHazard/tree/main/resources/S32_BPill_PCB/README.md), mounting points for two types of RTC modules are provided. For other PCBs, see below.

The RTC module connects to the Raspberry Pi via the I2C bus.  The following four pads on the RTC module need to be wired to the corresponding connections going to the Pi:  `Vin, GND, SCL, SDA`.  If using the DS3231 or PCF8523, the Vin pad can be wired to 3.3V or 5V.  For the DS1307 use 5V.  The other pads (besides those four) on the RTC module should be left unconnected.

Here is an example of wiring a DS3231 module via a Delta5 V2 PCB:

![DS3231 wiring](img/RH_DS3231_D5PCB.jpg)

If you're using one of the newer (Arduino-based) [RotorHazard PCBs &#10132;&#xFE0E;](https://github.com/RotorHazard/RotorHazard/tree/main/resources/PCB/README.md), there are several places on the board where these connections are available.

### Configuration

The following instructions apply to the standard [Raspberry Pi OS](https://www.raspberrypi.org/downloads/raspberry-pi-os) that is installed for RotorHazard.

Run the following command to verify that the RTC module is wired properly:
```
sudo i2cdetect -y 1
```
The response should look something like this:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- 08 -- 0a -- 0c -- 0e --
10: 10 -- 12 -- 14 -- 16 -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```
The "68" represents the I2C address of the RTC module.  (After the Pi is configured to use the module, this value changes to "UU".)  The addresses from "08" to "16" represent the installed Arduino nodes, and there will usually be 4 or 8 entries (matching the number of nodes).

Enter the following command to edit the "/boot/config.txt" file:
```
sudo nano /boot/config.txt
```
If using the DS3231, add the following line to the end of the file:
```
dtoverlay=i2c-rtc,ds3231
```
(If using the PCF8523, make it `dtoverlay=i2c-rtc,pcf8523`; if using the DS1307, make it `dtoverlay=i2c-rtc,ds1307`.)

Hit *Ctrl-O* and *Enter* to save the file and then *Ctrl-X* to exit the editor.

At this point, reboot the Pi:
```
sudo reboot
```
A startup-service file is needed to make the Pi read the time from the RTC module when the system starts up.  To create this file, enter the following command:
```
sudo nano /etc/systemd/system/hwclock-start.service
```
Copy and paste the text below into the editor:
```
[Unit]
Description=hwclock-start to read rtc and write to system clock
After=sysinit.target

[Service]
Type=oneshot
ExecStart=/sbin/hwclock --hctosys --utc

[Install]
WantedBy=basic.target
```
Hit *Ctrl-O* and *Enter* to save the file and then *Ctrl-X* to exit the editor.

To configure and enable this startup service, enter the following commands:
```
sudo chmod 644 /etc/systemd/system/hwclock-start.service
sudo chown root:root /etc/systemd/system/hwclock-start.service
sudo systemctl daemon-reload
sudo systemctl enable hwclock-start.service
sudo systemctl start hwclock-start.service
```
At this point the RTC module is installed and configured.  When the Pi starts up, it should read the date/time from the RTC module and always have the correct value.  If the Pi has an internet connection it will still use it to fetch the current date and time, and it will update the RTC module with the fetched date/time.

### Testing

Entering the `date` command will display the current system time of the Pi.

The command below may be used to verify the date/time values:
```
timedatectl status
```
The response should look something like this:
```
               Local time: Sat 2020-08-29 19:15:01 EDT
           Universal time: Sat 2020-08-29 23:15:01 UTC
                 RTC time: Sat 2020-08-29 23:15:01
                Time zone: America/New_York (EDT, -0400)
System clock synchronized: yes
              NTP service: active
          RTC in local TZ: no
```
If an RTC module is not installed or is not working properly, the third line in the response will be "RTC time: n/a".

The operation of the RTC startup service can be verified with the following command:
```
journalctl -b | grep 'hwclock-start to read rtc'
```
The response should contain one or more instances of lines similar to these:
```
Aug 29 19:01:49 pi3number98 systemd[1]: Starting hwclock-start to read rtc and write to system clock...
Aug 29 19:01:51 pi3number98 systemd[1]: Started hwclock-start to read rtc and write to system clock.
```

The current time held by RTC module can be queried via the `sudo hwclock -r` command.  Adding the -D parameter will provide additional information:  `sudo hwclock -D -r`

<br />

*References:*  The information in [this forum post](https://www.raspberrypi.org/forums/viewtopic.php?t=209700#p1572546) was used when creating these instructions.

-----------------------------

See Also:  
[doc/Hardware Setup.md](Hardware%20Setup.md)  
[doc/Software Setup.md](Software%20Setup.md)  
