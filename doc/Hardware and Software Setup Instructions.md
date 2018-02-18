# Hardware and Software Setup Instructions

## Parts List

### Receiver Node(s) (this list makes one node, build up to eight)
* 1 x Arduino Nano
* 1 x rx5808 with SPI mod (Receivers with date code 20120322 are known to work).
* 3 x 1k ohm resistor
* 1 x 100k ohm resistor
* 26 AWG and 30 AWG silicone wire

### System Components
* 1 x Raspberry Pi3 (Pi2 users have reported issues with multiple nodes connected)
* 8 GB (minimum) Micro SD Card
* 26 AWG and 30 AWG silicone wire (for wiring to each receiver node)
* 3D printed case for housing the electronics
* 5V power supply, 3 amp minimum

### Additional Components
* Ethernet cable, 50ft plus
* Outdoor power cable, 50ft plus
* Network router
* Laptop/tablet

## Hardware Setup

### RX5808 Video Receivers
Modify the rx5808 receivers to use SPI.

Remove the shield from the rx5808, the shield is normally held on by a few spots of solder around the edges. Use some solder wick to remove the solder and free the shield from the receiver. Be careful not to damage any ground pads on the receiver. There are usually small holes around the edge you can use to help push off the shield.

Remove the following resistor:
![rx5808 spi mod](img/rx5808-new-top.jpg)

The sheild should be soldered back in place after removing the resistor.

### Receiver Nodes
Complete wiring connections between each Arduino and RX5808.
![receiver node wiring](img/Receivernode.png)

### System Assembly
Complete wiring connections between each Arduino and the Raspberry Pi.

Note: be sure all Receiver Nodes and the Raspberry Pi are tied to a common ground; if not, the i2c messages can be corrupted.
![system wiring](img/D5-i2c.png)

## Software Setup

### Receiver Nodes (Arduinos)
Note: The latest Arduino IDE (1.8+) is required from https://www.arduino.cc/en/Main/Software

Open '/delta5_race_timer/src/delta5node/delta5node.ino' in the Arduino IDE.

Configure the '#define i2cSlaveAddress' line of the .ino for each node before uploading.
```
// Node Setup -- Set the i2c address here
// Node 1 = 8, Node 2 = 10, Node 3 = 12, Node 4 = 14
// Node 5 = 16, Node 6 = 18, Node 7 = 20, Node 8 = 22
#define i2cSlaveAddress 8
```

### System (Raspberry Pi)
Start by installing Raspbian, follow the official instructions here: https://www.raspberrypi.org/downloads/raspbian/, use 'RASPBIAN JESSIE WITH PIXEL'

Enable I2C on the Raspberry Pi, go to 'Advanced Options' and enable I2C.
```
sudo raspi-config
```

Install python and the python drivers for the GPIO.
```
sudo apt-get install python-dev
sudo apt-get install python-rpi.gpio
```

Final system update and upgrade.
```
sudo apt-get update && sudo apt-get upgrade
```

Clone or download this repo to '/home/pi/' on the Raspberry Pi.

Install web server packages, open a terminal in '/home/pi/delta5_race_timer/src/delta5server' and run
```
sudo pip install -r requirements.txt
```

## Starting the System

The following instructions will start the Delta5 Race Timer web server on the raspberry pi allowing full control and configuration of the system to run races and save lap times.  

Alternatively, to use your Delta5 Race Timer hardware with 3rd party timing software, replace each reference of 'delta5server' with 'timingserver' in the following instructions.

#### Manual Start
Open a terminal in '/delta5_race_timer/src/delta5server' and run
```
python server.py
```

#### Start on Boot
Create a service
```
sudo nano /lib/systemd/system/delta5.service
```
with the following contents
```
[Unit]
Description=Delta5 Server
After=multi-user.target

[Service]
WorkingDirectory=/home/pi/delta5_race_timer/src/delta5server
ExecStart=/usr/bin/python server.py

[Install]
WantedBy=multi-user.target
```
save and exit (CTRL-X, Y, ENTER).

Update permissions.
```
sudo chmod 644 /lib/systemd/system/delta5.service
```

Start on boot commands.
```
sudo systemctl daemon-reload
sudo systemctl enable delta5.service
sudo reboot
```
