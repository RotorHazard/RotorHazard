# Software Setup Instructions

- [Introduction](#introduction)
- [Install RotorHazard on a Raspberry Pi](#install-rotorhazard-on-a-raspberry-pi)
- [The Data Directory](#the-data-directory)
- [Running the RotorHazard Server](#running-the-rotorhazard-server)
- [RotorHazard Node Code](#rotorhazard-node-code)
- [Enable Port Forwarding](#enable-port-forwarding)
- [Optional Components](#optional-components)
- [Updating an Existing Installation](#updating-an-existing-installation)
- [Other Operating Systems](#other-operating-systems)
- [Viewing Database Files](#viewing-database-files)
- [RotorHazard Portable](#rotorhazard-portable)
- [Logging](#logging)

## Introduction

The central software component of the RotorHazard system is its server, written in Python, which operates its functions and serves up web pages to browsers. In a standard setup, the server is run on a [Raspberry Pi](https://www.raspberrypi.org). (It is also possible to run RotorHazard on other types of hardware -- see the [Other Operating Systems](#otheros) section below.)

Note: If RotorHazard is already installed, see the [Updating an existing installation](#update) section below.

Once the server is setup and running, see the RotorHazard Race Timer [User Guide](User%20Guide.md) for further instructions and setup tips.

## Install RotorHazard on a Raspberry Pi

### 1. Install the Raspberry Pi Operating System

Note: Many of the setup commands below require that the Rasperry Pi has internet access.

Install the Raspberry Pi OS, following the official instructions: https://www.raspberrypi.org/help

The standard-recommended setup is to use a Raspberry Pi 3, Pi 4 or Pi 5 board, install the [Raspberry Pi OS](https://www.raspberrypi.org/software/operating-systems/#raspberry-pi-os-32-bit) (Desktop), and configure it with a user named "pi".

Tip: Any time you intend to use a monitor (via HDMI) with the Raspberry Pi, connect it before powering up the Pi. Connecting the monitor after power up tends to not work (blank screen).


### 2. Configure Interface Options

(The options may be configured using step 2a or 2b below.)

#### 2a. Configure interface options using the desktop
If Raspberry Pi OS with Desktop was installed, the interface options may be configured via "Preferences" | "Raspberry Pi Configuration" | "Interfaces":
* Enable SSH, SPI, I2C, and 'Serial Port'
* Disable 'Serial Console'
* For remote access to the desktop (using a program like [RealVNC viewer](https://www.realvnc.com/en/connect/download/viewer)), enable VNC

#### 2b. Configure interface options using a terminal window
If the Pi OS Desktop is not available, the interface options may be configured using the following command:
```
sudo raspi-config
```
* Select 'Interface Options' and enable: SSH, SPI, and I2C
* Select 'Interface Options' | 'Serial Port', and configure:
  * "login shell accessible serial": No
  * "serial port hardware enabled": Yes


### 3. Apply Changes to the 'boot' _config.txt_ file
Open a terminal window and enter:
```
if [ -f "/boot/firmware/config.txt" ]; then sudo nano /boot/firmware/config.txt; else sudo nano /boot/config.txt; fi
```
Add the following lines to the end of the file:
```
dtparam=i2c_baudrate=75000
dtoverlay=miniuart-bt
```
If the Raspberry Pi in use is a Pi 3 model or older (not a Pi 4 or 5) then add this line:
```
core_freq=250
```
<a id="s32btconfig"></a>If your hardware is the S32_BPill setup with [shutdown button](Shutdown%20Button.md) and AUX LED then add these lines:
```
dtoverlay=act-led,gpio=24
dtparam=act_led_trigger=heartbeat
```
If the Raspberry Pi in use is a Pi 4 model or older (not a Pi 5) and your hardware is the S32_BPill setup with [shutdown button](Shutdown%20Button.md) then add this line:
```
dtoverlay=gpio-shutdown,gpio_pin=18,debounce=5000
```
If the Raspberry Pi in use is a Pi 5 model then add these lines:
```
dtoverlay=uart0-pi5
dtoverlay=i2c1-pi5
```
Save and exit the editor (CTRL-X, Y, ENTER)

*Notes:*

On newer versions of the Raspberry Pi OS, the boot-config file location is "/boot/firmware/config.txt". On older versions it is "/boot/config.txt".

The first line sets the transfer rate on the I2C bus (which is used to communicate with the Arduino node processors).

The "dtoverlay=miniuart-bt" line moves the high performance UART from the Bluetooth device to the GPIO pins, which is needed for setups like the S32_BPill that use the serial port as the communications channel to the nodes.

The "core_freq" line fixes a potential variable clock-rate issue, described [here](https://www.abelectronics.co.uk/kb/article/1089/i2c--smbus-and-raspbian-stretch-linux). If a Raspberry Pi 4 or Pi 5 is being used, the "core_freq" line should be omitted (as per the Raspberry Pi documentation [here](https://www.raspberrypi.org/documentation/configuration/config-txt/overclocking.md)).

For the S32_BPill setup, the "dtoverlay=act-led,gpio=24" and "dtparam=act_led_trigger=heartbeat" lines configure a Raspberry-Pi-heartbeat signal that the BPill processor monitors to track the status of the Pi. The "dtoverlay=gpio-shutdown..." line makes it so the shutdown button still operates if the RotorHazard server is not running.

If the Raspberry Pi 5 is being used, the "dtoverlay=uart0-pi5" and "dtoverlay=i2c1-pi5" lines configure the devices to operate similar to how they do with the Pi 3 & 4. 


### 4. Perform System Update
Using a terminal window, do a system update and upgrade (this can take a few minutes):
```
sudo apt update && sudo apt upgrade
```

<a id="python"></a>
### 5. Install Python
Using a terminal window, install Python and the Python drivers for the GPIO:
```
sudo apt install python3-dev python3-venv libffi-dev python3-smbus build-essential python3-pip git scons swig python3-rpi.gpio
```
Enter the following commands to setup the Python virtual environment:
```
cd ~
python -m venv --system-site-packages .venv
```
Configure the user shell to automatically activate the Python virtual environment by entering the command `nano .bashrc` to edit the ".bashrc" file and adding the following lines to the end of the file:
```
VIRTUAL_ENV_DISABLE_PROMPT=1
source ~/.venv/bin/activate
```
Save and exit the editor (CTRL-X, Y, ENTER)

### 6. Reboot System
After the above setup steps are performed, the system should be rebooted by entering the following using a terminal window:
```
sudo reboot
```

### 7. Install the RotorHazard Server

Go to the [Latest Release page](https://github.com/RotorHazard/RotorHazard/releases/latest) for the project and note the version code.

In the commands below, replace the two occurrences of "1.2.3" with the current version code, and enter the commands using a terminal window:

```bash
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/v1.2.3 -O temp.zip
unzip temp.zip
mv RotorHazard-1.2.3 RotorHazard
rm temp.zip
```

Install the RotorHazard server dependencies (be patient, this may take a few minutes):

```bash
cd ~/RotorHazard/src/server
pip install -r requirements.txt
```

### 8. Configuration File
When the RotorHazard server is run for the first time, it will create (in the data directory) a `config.json` file.

As of RotorHazard 4.3, it is not necessary to hand-edit this file. All settings can be modified within the frontend user interface. The `config.json` file may be directly edited to alter the configuration settings, but this must only be done while the RotorHazard server is not running, otherwise the changes will be overwritten. When the server starts up, if it detects that the `config.json` has been updated, it will load the settings and then create a backup copy of the file (with a filename in the form "config_bkp_YYYYMMDD_hhmmss.json").

The contents of the "config.json" file must be in valid JSON format. A validator utility like [JSONLint](https://jsonlint.com/) can be used to check for syntax errors.

----------------------------------------------------------------------------

## The Data Directory

It is recommended that users store their data in a separate data directory from the program files. This allows users to upgrade without manually copying files—simply replace the program directory with the new version. Prior to v4.3, RotorHazard would store these files in the program directory. If you start a server that was previously run this way, RotorHazard will offer to attempt a migration for you.

The data directory may contain:

* Event database (`/database.db`)
* Archived events and event database backups
* Configurtaion file (`/config.json`)
* Server logs (`/logs/`)
* A public front-end–accessible directory (`/shared/`)
* User-installed plugins (`/plugins/`) 

You may also wish to store your Python Virtual Environment here, and plugins may store additional files. The default data directory is `~/rh-data`, but any other location may be set.

### Setting the Data Directory

There are several options to specify your data directory, following an order of priority. Once a selection has been made, the other options are ignored.

#### 1: `--data` command-line arg
If you specify `--data <path>` on the command line when running the server, the location specified with `<path>` will be used.

#### 2: `datapath.ini`
If a `datapath.ini` file exists in the program directory and the location is valid, it will be used. If you ask RotorHazard to continue running in the program directory, it will write this file so the prompt does not reappear. Note that this method prevents some of the benefits of keeping data separate.

#### 3: `~/rh-data`, if it exists
If the `rh-data` directory exists in your operating system home/user directory, it will be used.

#### 4: Implicit run from program directory
If `config.json` exists in the program directory, the program direcotry will be used. The server will display a prompt on the `settings` page with a choice to migrate to `~/rh-data`.

#### 5: CWD contains config use CWD
if the current working directory of the operating system contains a `config.json` file, the current working directory will be used.

#### 6: Creating `~/rh-data`
The server will attempt to create `~/rh-data` and use it.

If the data directory cannot be selected, the server will not start.


----------------------------------------------------------------------------

## Running the RotorHazard Server

The following instructions will start the RotorHazard server on the Raspberry Pi, allowing full control and configuration of the system to run races and save lap times.

### Manual Start

Open a terminal window and enter the following:
```bash
cd ~/RotorHazard/src/server
python server.py
```
The server may be stopped by hitting Ctrl-C

Once the server is running, its web-GUI interface may be accessed in a browser; see the [Connect to the Server](User%20Guide.md#connect-to-the-server) section in the [User Guide](User%20Guide.md) for more information.

If no configuration file exists when the server is started, RotorHazard will prompt the user to confirm an admin username and password the first time the server frontend is accessed. You will need these credentials to access pages reserved for the race director (i.e., the *Settings* and *Run* pages).

### Start on Boot

To configure the system to automatically start the RotorHazard server when booting up:

Create a service file:
```bash
sudo nano /lib/systemd/system/rotorhazard.service
```

Copy and paste the following contents into the file:
```bash
[Unit]
Description=RotorHazard Server
After=multi-user.target

[Service]
User=pi
WorkingDirectory=/home/pi/RotorHazard/src/server
ExecStart=/home/pi/.venv/bin/python server.py

[Install]
WantedBy=multi-user.target
```

*Note*: If the username was configured as something other than "pi" during the Operating System setup, be sure to change the value `pi` in `User`, `WorkingDirectory` and `ExecStart` to match your username.

Save and exit (CTRL-X, Y, ENTER)

Enter the following command to update the service-file permissions:
```
sudo chmod 644 /lib/systemd/system/rotorhazard.service
```

Enter these commands to enable the service:
```
sudo systemctl daemon-reload
sudo systemctl enable rotorhazard.service
```
The service may now be started manually by entering the command `sudo systemctl start rotorhazard`, and should start up automatically when the Raspberry Pi is started up.

### Stopping the Server Service
If the RotorHazard server was started as a service during the boot, it may be stopped with a command like this:
```
sudo systemctl stop rotorhazard
```
To disable the service (so it no longer runs when the system starts up), enter:
```
sudo systemctl disable rotorhazard.service
```
To query the status of the service:
```
sudo systemctl status rotorhazard.service
```
If the service is running then the output will contain `Active: active (running)`. Hit the 'Q' key to exit the status command.

### Shutting Down the System
A system shutdown should always be performed before unplugging the power, either by clicking on the 'Shutdown' button on the 'Settings' page on the web GUI, or by entering the following in a terminal:
```
sudo shutdown now
```
The physical [shutdown button](Shutdown%20Button.md) may also be used on hardware that supports it.

----------------------------------------------------------------------------

## RotorHazard Node Code

The firmware for the RotorHazard nodes will need to be installed (or updated). The nodes can be Arduino based (with an Arduino processor for each node channel), or use the multi-node S32_BPill board (with a single STM32F1 processor running 1-8 channels).

For Arduino-based node boards, see the '[src/node/readme_Arduino.md](../src/node/readme_Arduino.md)' file for more information and instructions for installing the node firmware code.

For the S32_BPill board, the recommended method for installing the currently-released node firmware is to use the `Update Nodes` button (in the 'System' section on the 'Settings' page) on the RotorHazard web GUI.<br>
The "dtoverlay=miniuart-bt" line needs to have been added to the 'boot' _config.txt_ file for the flash-update to succeed (see instructions above).<br>
Note that the flash-update steps described in '[src/node/readme_S32_BPill.md](../src/node/readme_S32_BPill.md)' are for developers who wish to build the S32_BPill node firmware from the source code.

The node-code version may be viewed in the Server Log, and via the "About RotorHazard" item in the drop-down menu.

----------------------------------------------------------------------------

## Enable Port Forwarding
The RotorHazard server defaults to port 5000, as this is necessary for some 3rd party integrations. While you can change the port via `HTTP_PORT` in the `config.json` file, a better approach is often to forward the web default port of 80 to 5000.

By default, HTTP uses port 80. Other values will require that the port be included as part of the URL entered into client browsers. If other web services are running on the Pi, port 80 may already be in use and reusing it will cause problems. If port 80 is used directly via `HTTP_PORT`, the server may need to be run using the *sudo* command. With the following commands, the server runs on port 5000 but the system sends the traffic from port 80 to it.

```
sudo apt-get install iptables
sudo iptables -A PREROUTING -t nat -p tcp --dport 80 -j REDIRECT --to-ports 5000
sudo iptables -A PREROUTING -t nat -p tcp --dport 8080 -j REDIRECT --to-ports 80
sudo iptables-save
sudo apt-get install iptables-persistent
```
After running these commands, RotorHazard will be available from both ports 80 and 5000. When available by port 80, you may leave the port off when accessing the server, i.e.: `http://127.0.0.1`

Note: The second *iptables* command will forward port 8080 to 80, so services that would normally be available on port 80 will instead be available on port 8080. If port 80 services are not present or if other services are using port 8080, this *iptables* command may be omitted.
<br/>

----------------------------------------------------------------------------

## Optional Components

### Real Time Clock

The installation of a real-time clock module allows the RotorHazard timer to maintain the correct date and time even when an internet connection is not available. See '[doc/Real Time Clock.md](Real%20Time%20Clock.md)' for more information.

### WS2812b LED Support

Support for WS2812b LED strips (and panels) is provided by the Python library '[rpi-ws281x](https://github.com/rpi-ws281x/rpi-ws281x-python)', which is among the libraries installed via the `pip install -r requirements.txt` command.

The `LED_COUNT` value must be set in the `src/server/config.json` file (which must only be edited while the RotorHazard server is not running). The following items may be configured:
```
LED_COUNT:  Number of LED pixels in strip (or panel)
LED_ROWS:  Number of rows in a multiline LED display panel (LED_COUNT must be evenly divisible by this value; default 1)
LED_GPIO:  GPIO connected to the pixels (default 10 uses SPI '/dev/spidev0.0')
LED_FREQ_HZ:  LED signal frequency in hertz (usually 800000)
LED_DMA:  DMA channel to use for generating signal (default 10)
LED_INVERT:  True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL:  Set to '1' for GPIOs 13, 19, 41, 45 or 53
LED_STRIP:  Strip type and color ordering (default is 'GRB')
PANEL_ROTATE:  Optional panel-rotation value (default 0)
INVERTED_PANEL_ROWS:  Optional even-index row inversion for LED panels (default false)
```
`LED_GPIO` is not the hardware pin index.
If specified, the `LED_STRIP` value must be one of: 'RGB', 'RBG', 'GRB', 'GBR', 'BRG', 'BGR', 'RGBW', 'RBGW', 'GRBW',  'GBRW', 'BRGW', 'BGRW'

Running LEDs from certain GPIO pins (such as GPIO18) requires the server to be run as root. If the error message `Can't open /dev/mem: Permission denied` or `mmap() failed` appears on startup, you must connect LEDs to a different GPIO pin or run the server with `sudo`. If using a "rotorhazard.service" file to [start the server on boot](#start-on-boot), it may be run as root by leaving out the "User=pi" line.

See also the [WS2812b LED Support](Hardware%20Setup.md#ws2812b-led-support) section in [doc/Hardware Setup.md](Hardware%20Setup.md).

#### LED Panel Support

Additional LED effects for a two-dimensional LED display (panel) are available by installing image manipulation libraries.
```
sudo apt-get install libjpeg-dev
pip install pillow
sudo apt-get install libopenjp2-7-dev
```

- `LED_ROWS` **must be set** for multiline displays. 
- If your multiline panel image requires rotation, use `PANEL_ROTATE` with the number of 90-degree CCW rotations needed (0..3). 
- If alternating lines appear jumbled, try setting `INVERTED_PANEL_ROWS` to `true`.

#### LED Controller

An alternative to the above methods is to use an LED Controller module, which may be connected to a USB port on any computer that is running the RotorHazard Server. See the [LED Controller repository](https://github.com/RotorHazard/LEDCtrlr) for details on how to wire and program an Arduino board as an LED controller.

### Java Support
Java enables the calculating of IMD scores, which is helpful for selecting frequency sets with less interference between VTXs. To determine if Java is installed, run the following command:
```
java -version
```
If the response is "command not found" then Java needs to be installed.

For the Raspberry Pi 3 or newer, use the following command:
```
sudo apt install default-jdk-headless
```

For the Raspberry Pi Zero (or an older-model Pi), use this command:
```
sudo apt install openjdk-8-jdk-headless
```

----------------------------------------------------------------------------

<a id="update"></a>
## Updating an Existing Installation

Before updating, any currently-running RotorHazard server should be stopped. If installed as a service, it may be stopped with a command like:
```
sudo systemctl stop rotorhazard
```

To update an existing RotorHazard installation: Go to the [Latest Release page](https://github.com/RotorHazard/RotorHazard/releases/latest) for the project and note the version code. In the commands below, replace the two occurrences of "1.2.3" with the current version code, and enter the commands:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/v1.2.3 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-1.2.3 RotorHazard
rm temp.zip
cp RotorHazard.old/src/server/config.json RotorHazard/src/server/
cp RotorHazard.old/src/server/database.db RotorHazard/src/server/
```
The previous installation ends up in the 'RotorHazard.old' directory, which may be moved or deleted.

For RotorHazard the minimum version of Python supported is 3.9. If the installed version is Python 3.7 or older, see this [wiki article](https://github.com/RotorHazard/RotorHazard/wiki/Installing-Newer-Versions-of-Python-on-the-Raspberry-Pi) for a way to install a newer version of Python.

The RotorHazard server dependencies will also need to be updated (be patient, this command may take a few minutes):
```
cd ~/RotorHazard/src/server
pip install --upgrade --no-cache-dir -r requirements.txt
```

----------------------------------------------------------------------------

<a id="otheros"></a>
## Other Operating Systems

The RotorHazard server may be run on any computer with an operating system that supports Python. In these alternate configurations, one or more hardware nodes may be connected via USB -- see [doc/USB Nodes.md](USB%20Nodes.md) for more information. The server may also be run using simulated (mock) nodes.

**To install the RotorHazard server on these systems:**

1. If the computer does not already have Python installed, download and install Python from https://www.python.org/downloads . The minimum version of Python needed for RotorHazard is 3.9. To check if Python is installed and the version, open up a command prompt and enter ```python --version```

2. From the RotorHazard [Releases page on github](https://github.com/RotorHazard/RotorHazard/releases), download the "Source code (zip)" file.

3. Unzip the downloaded file into a directory (aka folder) on the computer.

4. Open up a command prompt and navigate to the topmost RotorHazard directory.

5. Create a Python virtual environment ('venv') by entering: ```python -m venv --system-site-packages .venv```

6. Activate the Python virtual environment ('venv'):

  * On a Windows system the command to use will likely be: ```.venv\Scripts\activate.bat```

  * On a Linux system the command to use will likely be: ```source .venv/bin/activate```

7. Using the same command prompt, navigate to the ```src/server``` directory in the RotorHazard files (using the 'cd' command).

8. Install the RotorHazard server dependencies using the 'reqsNonPi.txt' file, using one of the commands below. (Note that this command may require administrator access to the computer, and the command may take a few minutes to finish).

  * On a Windows system the command to use will likely be:<br/>```python -m pip install -r reqsNonPi.txt```<br>

Note: If the above command fails with a message like "error: Microsoft Visual C++ 14.0 is required", the "Desktop development with C++" Tools may be downloaded (from [here](https://aka.ms/vs/17/release/vs_BuildTools.exe)) and installed to satisfy the requirement.<br>

  * On a Linux system the command to use will likely be:<br/>```pip install -r reqsNonPi.txt```


**To run the RotorHazard server on these systems:**

1. Open up a command prompt and navigate to the topmost RotorHazard directory.

2. Activate the Python virtual environment ('venv')
  * On a Windows system the command to use will likely be: ```.venv\Scripts\activate.bat```

  * On a Linux system the command to use will likely be: ```source .venv/bin/activate```

3. Using the same command prompt, navigate to the ```src/server``` directory.

4. Enter: ```python server.py```

5. If the server starts up properly, you should see various log messages, including one like this:
    ```
    Running http server at port 5000
    ```

1. The server may be stopped by hitting Ctrl-C

If hardware nodes are connected via USB, they will need to be configured in the "SERIAL_PORTS" section in the "src/server/config.json" configuration file (see [doc/USB Nodes.md](USB%20Nodes.md) for details).

If no hardware nodes are configured, the server will operate using simulated (mock) nodes. In this mode the web-GUI interface may be explored and tested.

To view the web-GUI interface, open up a web browser and enter into the address bar: ```localhost:5000``` (If the HTTP_PORT value in the configuration has been changed then use that value instead of 5000). If the server is running then the RotorHazard main page should appear. Note that pages reserved for the race director (Admin/Settings) are password protected with the username and password specified in the configuration.

**To update an existing installation:**

1. From the RotorHazard [Releases page on github](https://github.com/RotorHazard/RotorHazard/releases), download the "Source code (zip)" file.

2. Unzip the downloaded file into the RotorHazard directory (aka folder) on the computer, overwriting the existing version.

3. Using the command prompt, navigate to the topmost RotorHazard directory.

4. Activate the Python virtual environment ('venv'):

  * On a Windows system the command to use will likely be: ```.venv\Scripts\activate.bat```

  * On a Linux system the command to use will likely be: ```source .venv/bin/activate```

5. Using the command prompt, navigate to the ```src/server``` directory.

6. Enter the update command:

  * On a Windows system the command to use will likely be:<br/>```python -m pip install --upgrade --no-cache-dir -r reqsNonPi.txt```

  * On a Linux system the command to use will likely be:<br/>```pip install --upgrade --no-cache-dir -r reqsNonPi.txt```
<br>

----------------------------------------------------------------------------

<a id="viewdb"></a>
## Viewing Database Files

A "snapshot" copy of the database file used by the RotorHazard server may be downloaded using the `Backup Database` button in the 'Data Management' section on the 'Format' page in the RotorHazard web GUI. A tool like [DB Browser for SQLite](https://sqlitebrowser.org) may be used to view the raw data in the file.

A database file may be loaded into the RotorHazard server via the "--viewdb" command-line argument:
```
python server.py --viewdb dbFileName.db [pagename] [browsercmd]
```
The current server database is backed up and the specified one is loaded. If a 'pagename' value (i.e., "results") is given then a web browser is launched showing the RotorHazard web GUI at the specified page. If a 'browsercmd' value is given then that command is used to launch the web browser (for instance, a value of "C:\Program Files\Mozilla Firefox\firefox.exe" could be specified to launch the Firefox browser on a PC where is it installed but is not the default browser).

The "--launchb" command-line argument can be specified to launch a web browser after the server starts up:
```
python server.py --launchb [pagename] [browsercmd]
```

----------------------------------------------------------------------------

<a id="portable"></a>
## RotorHazard Portable

A "portable" version of the RotorHazard server, which can be useful for viewing database files on a Windows PC, may be found [here](http://www.rotorhazard.com/portable). To use it, download the "rhPortable...zip" file, unpack it into a local directory, and then drag-and-drop a database file onto the 'runRotorHazard' batch file. This will launch a local copy of the RotorHazard server, load the database file, and launch a web browser for viewing the GUI. Sample RotorHazard database files may be found [here](http://www.rotorhazard.com/dbsamples). The server can be terminated by entering Ctrl-C on its console window.

(The "rhPortable...zip" file includes the needed Python support. The the 'runRotorHazardFF' batch file will attempt to launch the Firefox browser.)

----------------------------------------------------------------------------

<a id="logging"></a>
## Logging

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

When troubleshooting, another place to check for error messages is the system log file, which may be viewed with a command like: `journalctl -n 1000`


<br/>

-----------------------------

See Also:<br/>
[doc/Hardware Setup.md](Hardware%20Setup.md)<br/>
[doc/USB Nodes.md](USB%20Nodes.md)<br/>
[doc/User Guide.md](User%20Guide.md)<br/>
[Build Resources (PCB, etc) &#10132;&#xFE0E;](https://github.com/RotorHazard/RotorHazard/tree/main/resources/README.md)
