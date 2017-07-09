# Hardware and Software Setup Instructions

## Parts List

### Receiver Node(s) (this list makes one node, build up to eight)
* 1 x Arduino Nano
* 1 x rx5808 with SPI mod
* 3 x 1k ohm resistor
* 1 x 100k ohm resistor
* 26 AWG and 30 AWG silicone wire

### System Components
* 1 x Raspberry Pi2 or Pi3
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

1. Remove the shield from the rx5808. The shield is normally held on by a few spots of solder around the edges. Use some solder wick to remove the solder and free the shield from the receiver. Careful not to pull the shield off as the shield is connected to ground pads on the receiver. There are usually small holes around the edge you can use to help push off the shield.

2. Remove the following resistor:
![rx5808 spi mod](img/rx5808-new-top.jpg)

3. The sheild should be soldered back in place after removing the resistor.

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

1. Open '/delta5_race_timer/src/delta5node/delta5node.ino' in the Arduino IDE

2. Configure the '#define i2cSlaveAddress' line of the .ino for each node before uploading.
```
// Node Setup -- Set the i2c address here
// Node 1 = 8, Node 2 = 10, Node 3 = 12, Node 4 = 14
// Node 5 = 16, Node 6 = 18, Node 7 = 20, Node 8 = 22
#define i2cSlaveAddress 8
```

### System (Raspberry Pi)
1. Start by installing Raspbian, follow the official instructions here: https://www.raspberrypi.org/downloads/raspbian/, use 'RASPBIAN JESSIE WITH PIXEL'

2. Enable I2C on the Raspberry Pi
```
sudo raspi-config
```
go to 'Advanced Options' and enable I2C

3. Install Python
```
sudo apt-get install python-dev
```
and install the python drivers for the GPIO
```
sudo apt-get install python-rpi.gpio
```

4. Final Update and Upgrade
```
sudo apt-get update && sudo apt-get upgrade
```

5. Clone or download this repo to '/home/pi/' on the Raspberry Pi

6. Additional Python Packages

Open a terminal in '/home/pi/delta5_race_timer/src/delta5server' and run
```
sudo pip install -r requirements.txt
```

## Starting the System

The following instructions will start the Delta5 Race Timer web server on the raspberry pi allowing full control and configuration of the system to run races and save lap times.  

Alternatively, to use your Delta5 Race Timer hardware with 3rd party timing software, replace each reference of 'delta5server' with 'timingserver' in the following instructions.

#### Manual Start
1. Open a terminal in '/delta5_race_timer/src/delta5server' and run
```
python server.py
```

#### Start on Boot
1. Create a service
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
save and exit (CTRL-X, Y, ENTER)

2. Update permissions
```
sudo chmod 644 /lib/systemd/system/delta5.service
```

3. Start on boot
```
sudo systemctl daemon-reload
sudo systemctl enable delta5.service
sudo reboot
```
