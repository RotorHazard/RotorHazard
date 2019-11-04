# Software Setup Instructions

## Install System (Raspberry Pi)
Note: Many of the setup commands below require that the Rasperry Pi has internet access.

Start by installing Raspbian, following the official instructions here: https://www.raspberrypi.org/downloads/raspbian/. You may use either Desktop or Lite.

Configure the interface options on the Raspberry Pi.
Open a Terminal window and enter the following command:
```
sudo raspi-config
```
Select Interfacing Options and enable: SSH, SPI, and I2C.

Do system update and upgrade (this can take a few minutes):
```
sudo apt-get update && sudo apt-get upgrade
```

Install Python and the Python drivers for the GPIO.
```
sudo apt-get install python-dev python-rpi.gpio libffi-dev python-smbus build-essential python-pip git scons swig
```

Install the function interface into Python
```
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
Save and exit the file with Ctrl-X

Install the RotorHazard code under '/home/pi/' on the Raspberry Pi as follows: Go to the [Latest Release page](https://github.com/RotorHazard/RotorHazard/releases/latest) for the project and note the version code. In the commands below, replace the two occurrences of "1.1.0" with the current version code, and enter the commands:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/v1.1.0 -O temp.zip
unzip temp.zip
mv RotorHazard-1.1.0 RotorHazard
rm temp.zip
```

Install web server dependencies:
Be patient, this command may take a few minutes.
```
cd /home/pi/RotorHazard/src/server
sudo pip install -r requirements.txt
```

Update permissions in working folder:
```
cd ~
cd /home/pi/RotorHazard/src
sudo chmod 777 server
```

## Install Receiver Node Code (Arduinos)
Arduino 1.8+ is required. Download from https://www.arduino.cc/en/Main/Software

*The node code and the server version must match. Use the file included with the server code you downloaded earlier; do not download a different file directly from GitHub.*

Open 'RotorHazard/src/node/node.ino' in the Arduino IDE.

Configure the '#define NODE_NUMBER' line of the .ino for each node before uploading. For first node set NODE_NUMBER to 1, for second set it to 2, etc.
```
// Node Setup -- Set node number here (1 - 8)
#define NODE_NUMBER 1
```

Automatic node configuration is also possible by grounding of hardware pins. Set NODE_NUMBER to 0, then tie these pins to ground:
node #1: ground pin D5
node #2: ground pin D6
node #3: ground pin D7
node #4: ground pin D8
node #5: ground pin D5 and pin D4
node #6: ground pin D6 and pin D4
node #7: ground pin D7 and pin D4
node #8: ground pin D8 and pin D4

## Install Optional Components
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

### INA219 Voltage/Current Support
The ina219 interface is provided by the following project:
https://github.com/chrisb2/pi_ina219

Clone the repository onto the Pi:
```
cd ~
sudo git clone https://github.com/chrisb2/pi_ina219.git
cd pi_ina219
```
Install the Python library:
```
sudo python setup.py install
```

### BME280 Temperature Support
The bme280 interface is provided by the following project:
https://github.com/rm-hull/bme280

Clone the repository onto the Pi:
```
cd ~
sudo git clone https://github.com/rm-hull/bme280.git
cd bme280
```
Install the Python library:
```
sudo python setup.py install
```

### Java Support
Java enables calculating of IMD scores. If you started with RASPBIAN WITH DESKTOP, this step should not be necessary as Java is installed by default. Otherwise:
```
sudo apt-get install oracle-java8-jdk
```

## Prepare System
### Reboot System
After the above setup steps are performed, the system should be rebooted by entering the following:
```
sudo reboot
```

### Starting the System

The following instructions will start the web server on the raspberry pi, allowing full control and configuration of the system to run races and save lap times.

#### Manual Start
Open a terminal and enter the following:
```
cd /home/pi/RotorHazard/src/server
python server.py
```
The server may be stopped by hitting Ctrl-C

#### Start on Boot
Create a service
```
sudo nano /lib/systemd/system/rotorhazard.service
```
with the following contents
```
[Unit]
Description=RotorHazard Server
After=multi-user.target

[Service]
WorkingDirectory=/home/pi/RotorHazard/src/server
ExecStart=/usr/bin/python server.py

[Install]
WantedBy=multi-user.target
```
save and exit (CTRL-X, Y, ENTER).

Update permissions.
```
sudo chmod 644 /lib/systemd/system/rotorhazard.service
```

Start on boot commands.
```
sudo systemctl daemon-reload
sudo systemctl enable rotorhazard.service
sudo reboot
```

### Shutting down the System
A system shutdown should always be performed before unplugging the power, either by clicking on the 'Shutdown' button on the 'Settings' page, or by entering the following in a terminal:
```
sudo shutdown now
```

-----------------------------

See Also:
[doc/Hardware Setup.md](Hardware%20Setup.md)
[doc/User Guide.md](User%20Guide.md)
