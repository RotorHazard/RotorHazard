# Hardware and Software Setup Instructions

## Parts List

### Receiver Node(s) (this is enough for one receiver node, build as many as needed)
* 1 x Arduino Nano
* 1 x rx5808 with SPI mod
* 3 x 1k ohm resistor
* 1 x 100k ohm resistor
* 26 AWG and 30 AWG silicone wire

### Main Controller
* 1 x Raspberry Pi2 or Pi3
* 8 GB (minimum) Micro SD Card
* 26 AWG and 30 AWG silicone wire (for wiring to each receiver node)

### The Rest
* 3D printed case for the electronics
* 3 amp minimum 5V power supply
* Ethernet cable, 50ft plus
* Outdoor power cable, 50ft plus
* Network router
* Laptop/tablet

## Hardware Setup

### RX5808
You will have to modify the rx5808 receiver so that it can use SPI.

1. Remove the shield from the rx5808. The shield is normally held on by a few spots of solder around the edges.  Use some solder wick to remove the solder and free the shield from the receiver.  Careful not to pull the shield off as the shield is connected to ground pads on the receiver. There are usually small holes around the edge you can use to help push off the shield.

2. Remove the following resistor:
![alt text](img/rx5808-new-top.jpg)

3. The sheild should be soldered back in place after removing the resistor.

### Receiver Node(s)
Complete wiring connections between each Arduino and RX5808.
![alt text](img/Receivernode.png)

### Main Controller
Complete wiring connections between each Arduino and the Raspberry Pi.
Note: be sure all Receiver Nodes and the Raspberry Pi are tied to a common ground; if not, the i2c messages can be corrupted.
![alt text](img/D5-i2c.png)

## Software Setup

### Raspberry Pi
1. Start by instaling Raspbian, follow the official instructions here: https://www.raspberrypi.org/downloads/raspbian/, use 'RASPBIAN JESSIE WITH PIXEL'

2. Enable I2C on the Raspberry Pi
```
sudo raspi-config
```
Go to Advanced Options, and enable I2C

3. Install Python
```
sudo apt-get install python-dev
```
and install the python drivers for the GPIO
```
sudo apt-get install python-rpi.gpio
```

4. Final Update and upgrade
```
sudo apt-get update && sudo apt-get upgrade
```

5. Clone or download this repo to '/home/pi/' on the Raspberry Pi

6. Open a terminal in '/delta5_race_timer/src/delta5server' and run
```
sudo pip install -r requirements.txt
```

### Receiver Node Arduino Code:
1. Open '/delta5_race_timer/src/delta5node/delta5node.ino' in the Arduino IDE

2. Configure 'i2cSlaveAddress' in the setup section of the .ino

3. Upload to each Arduino receiver node changing 'i2cSlaveAddress' each time

### Start the Server

There are two types of servers that the pi can run to collect timing data.  The following instructions are for a hosted webapp that can be used to do everything needed to run a race and collect times.  

The other alternative is a slimmed down timing server intended to be used to communicate with external timing software.  If you wish to use the timing server, replace "delta5server" with "timingserver" in the paths provided in the following instructions.

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
