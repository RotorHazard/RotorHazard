# Software Setup Instructions

The central software component of the RotorHazard system is its server, written in Python, which operates its functions and serves up web pages to browsers. In a standard setup, the server is run on a RaspberryPi. (It is also possible to run RotorHazard on other types of hardware -- see the [Other Operating Systems](#otheros) section below.)

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
sudo apt install python-dev libffi-dev python-smbus build-essential python-pip git scons swig python-rpi.gpio
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
Note: The first line sets the transfer rate on the I2C bus (which is used to communicate with the Arduino node processors). The second line fixes a potential variable clock-rate issue, described [here](https://www.abelectronics.co.uk/kb/article/1089/i2c--smbus-and-raspbian-stretch-linux). If a Raspberry Pi 4 is being used, the second line may need to be omitted.

Save and exit the file with Ctrl-X

Install the RotorHazard code under '/home/pi/' on the Raspberry Pi as follows: Go to the [Latest Release page](https://github.com/RotorHazard/RotorHazard/releases/latest) for the project and note the version code. In the commands below, replace the two occurrences of "1.2.3" with the current version code, and enter the commands:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/1.2.3 -O temp.zip
unzip temp.zip
mv RotorHazard-1.2.3 RotorHazard
rm temp.zip
```

Install RotorHazard server dependencies (be patient, this command may take a few minutes):
```
cd ~/RotorHazard/src/server
sudo pip install -r requirements.txt
```

Update permissions in working folder:
```
cd ~/RotorHazard/src
sudo chmod 777 server
```

*Note: If RotorHazard is already installed, see the [Updating an existing installation](#update) section below.*

## Install Receiver Node Code (Arduinos)
Arduino 1.8+ is required. Download from https://www.arduino.cc/en/Main/Software

*The node code and the server version must match. Use the 'node' code included with the server code you downloaded earlier; do not download a different file directly from GitHub.*

The node code may be edited and built using the [Eclipse IDE](https://www.eclipse.org/eclipseide/) and the "[Eclipse C++ IDE for Arduino](https://marketplace.eclipse.org/content/eclipse-c-ide-arduino)" plugin (or the old-fashioned way using the Arduino IDE). In Eclipse, the node-code project may be loaded via "File | Open Projects from File System..."

If you are not using a RotorHazard PCB, edit the 'src/node/config.h' file and configure the '#define NODE_NUMBER' value for each node before uploading. For first node set NODE_NUMBER to 1, for second set it to 2, etc.
```
// Node Setup -- Set node number here (1 - 8)
#define NODE_NUMBER 1
```

Hardware address selection is also possible by grounding hardware pins following the [published specification](https://github.com/RotorHazard/RotorHazard/wiki/Specification:-Node-hardware-addressing).

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

Note: The **LED_COUNT** value will need to be set in the `src/server/config.json` file. See the `src/server/config-dist.json` file for the default configuration of the 'LED' settings.  The following items may be set:
```
LED_COUNT:  Number of LED pixels in strip (or panel)
LED_PIN:  GPIO pin connected to the pixels (default 10 uses SPI '/dev/spidev0.0')
LED_FREQ_HZ:  LED signal frequency in hertz (usually 800000)
LED_DMA:  DMA channel to use for generating signal (default 10)
LED_INVERT:  True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL:  Set to '1' for GPIOs 13, 19, 41, 45 or 53
LED_STRIP:  Strip type and color ordering (default is 'GRB')
LED_ROWS:  Number of rows in LED-panel array (1 for strip)
PANEL_ROTATE:  Optional panel-rotation value (default 0)
INVERTED_PANEL_ROWS:  Optional panel row-inversion (default false)
```
If specified, the **LED_STRIP** value must be one of: 'RGB', 'RBG', 'GRB', 'GBR', 'BRG', 'BGR', 'RGBW', 'RBGW', 'GRBW',  'GBRW', 'BRGW', 'BGRW'

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
sudo apt-get install openjdk-8-jdk
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
cd ~/RotorHazard/src/server
python server.py
```
The server may be stopped by hitting Ctrl-C

#### Start on Boot
To configure the system to automatically start the RotorHazard server when booting up:

Create a service file:
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

Update permissions:
```
sudo chmod 644 /lib/systemd/system/rotorhazard.service
```

Enable the service:
```
sudo systemctl daemon-reload
sudo systemctl enable rotorhazard.service
sudo reboot
```
#### Stopping the server service
If the RotorHazard server was started as a service during the boot, it may be stopped with a command like this:
```
sudo systemctl stop rotorhazard
```
To disable the service (so it no longer runs when the system starts up), enter:
```
sudo systemctl disable rotorhazard.service
```

### Shutting down the System
A system shutdown should always be performed before unplugging the power, either by clicking on the 'Shutdown' button on the 'Settings' page, or by entering the following in a terminal:
```
sudo shutdown now
```

<a id="update"></a>
### Updating an existing installation

Before updating, any currently-running RotorHazard server should be stopped. If installed as a service, it may be stopped with a command like:
```
sudo systemctl stop rotorhazard
```

To update an existing RotorHazard installation: Go to the [Latest Release page](https://github.com/RotorHazard/RotorHazard/releases/latest) for the project and note the version code. In the commands below, replace the two occurrences of "1.2.3" with the current version code, and enter the commands:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/1.2.3 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-1.2.3 RotorHazard
rm temp.zip
cp RotorHazard.old/src/server/config.json RotorHazard/src/server/
cp RotorHazard.old/src/server/database.db RotorHazard/src/server/
```
The previous installation ends up in the 'RotorHazard.old' directory, which may be deleted or moved.

The RotorHazard server dependencies should also be updated (be patient, this command may take a few minutes):
```
cd ~/RotorHazard/src/server
sudo pip install --upgrade --no-cache-dir -r requirements.txt
```
<br/>

-----------------------------

<a id="otheros"></a>
### Other Operating Systems

The RotorHazard server may be run on any computer with an operating system that supports Python. In these alternate configurations, one or more hardware nodes may be connected via USB -- see [doc/USB Nodes.md](USB%20Nodes.md) for more information. The server may also be run using simulated (mock) nodes.

To install the RotorHazard server on these systems:

1. If the computer does not already have Python installed, download and install Python version 2.7 from https://www.python.org/downloads . To check if Python is installed, open up a command prompt and enter ```python --version```

1. From the RotorHazard [Releases page on github](https://github.com/RotorHazard/RotorHazard/releases), download the "Source code (zip)" file.

1. Unzip the downloaded file into a directory (aka folder) on the computer.

1. Open up a command prompt and navigate to the ```src/server``` directory in the RotorHazard files (using the 'cd' command).

1. Install the RotorHazard server dependencies using the 'requirements.txt' file, using one of the commands below. (Note that this command may require administrator access to the computer, and the command may take a few minutes to finish).
  * On a Windows system the command to use will likely be:<br/>```python -m pip install -r requirements.txt```<br/><br/>
  * On a Linux system the command to use will likely be:<br/>```sudo pip install -r requirements.txt```<br/>


To run the RotorHazard server on these systems:

1. Open up a command prompt and navigate to the ```src/server``` directory in the RotorHazard files (if not already there).

1. Enter: ```python server.py```

1. If the server starts up properly, you should see various log messages, including one like this:
    ```
    Running http server at port 5000
    ```

1. The server may be stopped by hitting Ctrl-C

If hardware nodes are connected via USB, they will need to be configured in the "SERIAL_PORTS" section in the "src/server/config.json" configuration file (see [doc/USB Nodes.md](USB%20Nodes.md) for details).

If no hardware nodes are configured, the server will operate using simulated (mock) nodes. In this mode the web-GUI interface may be explored and tested.

To view the web-GUI interface, open up a web browser and enter into the address bar: ```localhost:5000``` (If the HTTP_PORT value in the configuration has been changed then use that value instead of 5000). If the server is running then the RotorHazard main page should appear. Note that pages reserved for the race director (Admin/Settings) are password protected with the username and password specified in the configuration.

<br/>

-----------------------------

See Also:<br/>
[doc/Hardware Setup.md](Hardware%20Setup.md)<br/>
[doc/USB Nodes.md](USB%20Nodes.md)<br/>
[doc/User Guide.md](User%20Guide.md)
