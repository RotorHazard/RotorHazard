# Software Setup Instructions

The central software component of the RotorHazard system is its server, written in Python, which operates its functions and serves up web pages to browsers. In a standard setup, the server is run on a RaspberryPi. (It is also possible to run RotorHazard on other types of hardware -- see the [Other Operating Systems](#otheros) section below.)

Note: If RotorHazard is already installed, see the [Updating an existing installation](#update) section below.

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

## Install Receiver Node Code (Arduinos)
The standard method of loading (or flashing) the node code onto the Arduino processors (one for each node) is by loading the code into the Arduino IDE program and using its 'Upload' function.  Arduino IDE version 1.8 or newer is required, and it can be download from https://www.arduino.cc/en/Main/Software

The code for the Arduino nodes is in the `src/node` directory. To get these files onto your computer, go to the [RotorHazards releases page on GitHub](https://github.com/RotorHazard/RotorHazard/releases) and download the .zip file for the release you're installing (*make sure it is the same release as the one you installed on the Raspberry Pi*).  For instance, if you're installing version 2.2.0, go to the release page for [that version](https://github.com/RotorHazard/RotorHazard/releases/tag/2.2.0), click on "Source code (zip)" and download the file, which in this case will be "RotorHazard-2.2.0.zip".  Unpack that .zip file into a directory on your computer, and the `src/node` directory will be in there.

In the Arduino IDE, select "File | Open" and navigate to where the `src/node` directory is located, and click on the "node.ino" file to open the node-code project.  In the Arduino IDE the board type (under "Tools") will need to be set to match the Arduino -- the standard setup is:  for 'Board' select "Arduino Nano" and for 'Processor' select "ATMega328P" or "ATMega328P (Old Bootloader)", depending on the particular Arduino used.  If all is well, clicking on the 'Verify' button will successfully compile the code

Using the Arduino IDE, the Arduino processors for the nodes are programmed (flashed) one at a time.  The target Arduino is plugged into the computer via its USB connector -- when connected, it will be assigned a serial-port name (like "COM3").  In the Arduino IDE the serial port (under "Tools | Port") will need to be set to match the connected Arduino.  (If you view the "Tools | Port" selections before and after connecting the Arduino, you should see its serial-port name appear.)  Clicking on the 'Upload' button should flash the code onto the Arduino processor.

If you are not using a [RotorHazard PCB](../resources/PCB/README.md), edit the `src/node/config.h` file and configure the '#define NODE_NUMBER' value for each node before uploading. For first node set NODE_NUMBER to 1, for second set it to 2, etc.
```
// Node Setup -- Set node number here (1 - 8)
#define NODE_NUMBER 1
```

Hardware address selection is also possible by grounding hardware pins following the [published specification](https://github.com/RotorHazard/RotorHazard/wiki/Specification:-Node-hardware-addressing) (this is how the Arduinos are wired on the [RotorHazard PCB](../resources/PCB/README.md)).

The node code may also be edited and built using the [Eclipse IDE](https://www.eclipse.org/eclipseide/) and the "[Eclipse C++ IDE for Arduino](https://marketplace.eclipse.org/content/eclipse-c-ide-arduino)" plugin. In Eclipse, the node-code project may be loaded via "File | Open Projects from File System..."

### Verify Arduino Addresses

Run the following command to verify that the Arduinos are wired and programmed properly:
```
sudo i2cdetect -y 1
```
On an setup with 8 nodes the response should look something like this:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- 08 -- 0a -- 0c -- 0e --
10: 10 -- 12 -- 14 -- 16 -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```
The "08" through "16" values represent the presence of each Arduino at its address (in hexadecimal, 08 for node 1, 0a for node 2, etc).  On a setup with 4 nodes only the first four addresses will appear.

## Install Optional Components

### Real Time Clock

The installation of a real-time clock module allows the RotorHazard timer to maintain the correct date and time even when an internet connection is not available.  See '[doc/Real Time Clock.md](Real%20Time%20Clock.md)' for more information.

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

The LED library requires direct memory and GPIO access. When enabled, RotorHazard must be run with `sudo`.
```
sudo python server.py
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

### Enable Port forwarding
The RotorHazard server defaults to port 5000, as this is necessary for some 3rd party integrations. While you can change the port via `HTTP_PORT` in the `config.json` file, a better approach is often to forward the web default port of 80 to 5000.

By default, HTTP uses port 80. Other values will require that the port be included as part of the URL entered into client browsers. If other web services are running on the Pi, port 80 may already be in use and reusing it will cause problems. If port 80 is used directly via `HTTP_PORT`, the server may need to be run using the *sudo* command. With the following commands, the server runs on port 5000 but the system sends the traffic from port 80 to it.

```
sudo iptables -A PREROUTING -t nat -p tcp --dport 80 -j REDIRECT --to-ports 5000
sudo iptables-save
sudo apt-get install iptables-persistent
```
After running these commands, RotorHazard will be available from both ports 80 and 5000. When available by port 80, you may leave the port off when accessing the server: `http://127.0.0.1`
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

<a id="logging"></a>
### Logging

The RotorHazard server generates "log" messages containing information about its operations. Below is a sample configuration for logging:

```
    "LOGGING": {
        "CONSOLE_LEVEL": "INFO",
        "SYSLOG_LEVEL": "NONE",
        "FILELOG_LEVEL": "INFO",
        "FILELOG_NUM_KEEP": 30,
        "CONSOLE_STREAM": "stdout"
    }
```
The following log levels may be specified:  DEBUG, INFO, WARNING, WARN, ERROR, FATAL, CRITICAL, NONE

If the FILELOG_LEVEL value is not NONE then the server will generate log files in the `src/server/logs` directory. A new log file is created each time the server starts, with each file having a unique name based on the current date and time (i.e., "rh_20200621_181239.log"). Setting FILELOG_LEVEL to DEBUG will result in more detailed log messages being stored in the log file, which can be useful when debugging problems.

The FILELOG_NUM_KEEP value is the number of log files to keep; the rest will be deleted (oldest first).

The CONSOLE_STREAM value may be "stdout" or "stderr".

If the SYSLOG_LEVEL value is not NONE then the server will send log messages to the logging utility built into the host operating system.

The current Server Log may be displayed via the "View Server Log" item in the drop-down menu. The displayed log is "live" in that it will update as new messages are generated. The log can be displayed in a separate window by clicking on the "View Server Log" menu item with the right-mouse button and selecting the "Open Link in New Window" (or similar) option.

Clicking on the "Select Text" button will select all the displayed log text, which may then be copied and pasted. Clicking on the "Download Logs" button will create and download a '.zip' archive file containing all available log files and the current configuration and database files. The '.zip' archive file can also be generated by running the server with the following command:  `python server.py --ziplogs`

**When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended.**

When troubleshooting, another place to check for error messages is the "/var/log/syslog" file, which may be viewed with a command like: `tail -100 /var/log/syslog`


<br/>

-----------------------------

See Also:<br/>
[doc/Hardware Setup.md](Hardware%20Setup.md)<br/>
[doc/USB Nodes.md](USB%20Nodes.md)<br/>
[doc/User Guide.md](User%20Guide.md)<br/>
[Build Resources (PCB, etc)](../resources)
