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
* ws2812b LEDs

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

### WS2812b LED Support
The pins in the green box is what were already used by the timer. The pins in the red box is where you connect the signal and ground from the ws2812b LEDs.  The LEDs will require a separate power source. See WS2812b LED support under Software Setup.
![led wiring](img/GPIO.jpg)

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
Start by installing Raspbian, follow the official instructions here: https://www.raspberrypi.org/downloads/raspbian/, use 'RASPBIAN STRETCH WITH DESKTOP'

Configure the interface options on the Raspberry Pi.
Open a Terminal window and enter the following command:
```
sudo raspi-config
```
Select Interfacing Options and enable: SSH, SPI, and I2C.


Install python and the python drivers for the GPIO.
```
sudo apt-get update 
sudo apt-get upgrade
sudo apt-get install python-dev python-rpi.gpio libffi-dev python-smbus build-essential python-pip git scons swig
sudo pip install cffi
```

Update i2c baud rate
```
sudo nano /boot/config.txt
```
add the following lines to the end of the file:
```
dtparam=i2c_baudrate=75000
core_freq=250
```
Save and exit the file with Ctrl-x


### WS2812b LED Support
The ws2812b controls are provided by the following project:
https://github.com/jgarff/rpi_ws281x


Clone the repository onto the Pi and initiate Scons:
```
cd ~
sudo git clone https://github.com/jgarff/rpi_ws281x.git
cd rpi_ws281x
sudo scons
```
Install the Python library:
```
cd python
sudo python setup.py install
```

Clone or download this repo to '/home/pi/' on the Raspberry Pi.
```
cd ~
git clone https://github.com/scottgchin/delta5_race_timer.git
```

System update and upgrade.
```
sudo apt-get update && sudo apt-get upgrade
```

Install web server packages
```
cd /home/pi/delta5_race_timer/src/delta5server
sudo pip install -r requirements.txt
```

Update permissions in working folder
```
cd ~
cd /home/pi/delta5_race_timer/src
 
```

## Reboot System
```
sudo reboot
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
