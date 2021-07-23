# Software Setup Instructions

The central software component of the RotorHazard system is its server, written in Python, which operates its functions and serves up web pages to browsers. In a standard setup, the server is run on a RaspberryPi. (It is also possible to run RotorHazard on other types of hardware -- see the [Other Operating Systems](#otheros) section below.)

Note: If RotorHazard is already installed, see the [Updating an existing installation](#update) section below.

## Install RotorHazard on a Raspberry Pi

### 1. Install the Raspberry Pi Operating System

Note: Many of the setup commands below require that the Rasperry Pi has internet access.

Install the Raspberry Pi OS, following the official instructions: https://www.raspberrypi.org/help

The standard-recommended setup is to use a Raspberry Pi 3 board and install the [Raspberry Pi OS](https://www.raspberrypi.org/software/operating-systems/#raspberry-pi-os-32-bit) (32-bit, Desktop).

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


### 3. Apply Changes to '/boot/config.txt'
Open a terminal window and enter:

```
sudo nano /boot/config.txt
```
Add the following lines to the end of the file:

```
dtparam=i2c_baudrate=75000
dtoverlay=miniuart-bt
```
If the Raspberry Pi in use is a Pi 3 model or older (not a Pi 4) then also add this line:

```
core_freq=250
```
<a id="s32btconfig"></a>If your hardware is the S32_BPill setup with [shutdown button](Shutdown%20Button.md) and AUX LED then add these lines:

```
dtoverlay=act-led,gpio=24
dtparam=act_led_trigger=heartbeat
dtoverlay=gpio-shutdown,gpio_pin=18,debounce=5000
```
Save and exit (CTRL-X, Y, ENTER)

The first line sets the transfer rate on the I2C bus (which is used to communicate with the Arduino node processors).

The "dtoverlay=miniuart-bt" line moves the high performance UART from the Bluetooth device to the GPIO pins, which is needed for setups like the S32_BPill that use the serial port as the communications channel to the nodes.

The "core_freq" line fixes a potential variable clock-rate issue, described [here](https://www.abelectronics.co.uk/kb/article/1089/i2c--smbus-and-raspbian-stretch-linux). If a Raspberry Pi 4 is being used, the "core_freq" line should be omitted (as per the Raspberry Pi documentation [here](https://www.raspberrypi.org/documentation/configuration/config-txt/overclocking.md)).

For the S32_BPill setup, the "dtoverlay=act-led,gpio=24" and "dtparam=act_led_trigger=heartbeat" lines configure a Raspberry-Pi-heartbeat signal that the BPill processor monitors to track the status of the Pi.  The "dtoverlay=gpio-shutdown..." line makes it so the shutdown button still operates if the RotorHazard server is not running.


### 4. Perform System Update
Using a terminal window, do a system update and upgrade (this can take a few minutes):

```
sudo apt-get update && sudo apt-get upgrade
```

<a id="python"></a>
### 5. Install Python
Using a terminal window, install Python and the Python drivers for the GPIO:

```
sudo apt install python-dev python3-dev libffi-dev python-smbus build-essential python-pip python3-pip git scons swig python-rpi.gpio python3-rpi.gpio
```
Check the current default version of Python by entering the following command:

```
python --version
```
If the version reported is older than Python 3, enter the following commands to switch the default version to Python 3:

```
sudo update-alternatives --install /usr/bin/python python /usr/bin/python2 1
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 2
```
After the above commands are entered, the system should default to using Python 3. The default version can be switched back and forth via the command: `sudo update-alternatives --config python`

### 6. Install the RotorHazard Server
Install the RotorHazard server code under '/home/pi/' on the Raspberry Pi as follows:

Go to the [Latest Release page](https://github.com/RotorHazard/RotorHazard/releases/latest) for the project and note the version code.

In the commands below, replace the two occurrences of "1.2.3" with the current version code, and enter the commands using a terminal window:

```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/1.2.3 -O temp.zip
unzip temp.zip
mv RotorHazard-1.2.3 RotorHazard
rm temp.zip
```

Enter the commands below to install RotorHazard server dependencies (be patient, this may take a few minutes):

```
cd ~/RotorHazard/src
sudo python3 -m pip install -r requirements.txt
```

### 7. Reboot System
After the above setup steps are performed, the system should be rebooted by entering the following using a terminal window:

```
sudo reboot
```

----------------------------------------------------------------------------

## RotorHazard Node Code

The firmware for the RotorHazard nodes will need to be installed (or updated). The nodes can be Arduino based (with an Arduino processor for each node channel), or use the multi-node S32_BPill board (with a single STM32F1 processor running 1-8 channels).

For Arduino-based node boards, see the '[src/node/readme_Arduino.md](../src/node/readme_Arduino.md)' file for more information and instructions for installing the node firmware code.

For the S32_BPill board, the recommended method for installing the currently-released node firmware is to use the `Update Nodes` button (in the 'System' section on the 'Settings' page) on the RotorHazard web GUI.<br>
The "dtoverlay=miniuart-bt" line needs to have been added to the "/boot/config.txt" file for the flash-update to succeed (see instructions above).<br>
Note that the flash-update steps described in '[src/node/readme_S32_BPill.md](../src/node/readme_S32_BPill.md)' are for developers who wish to build the S32_BPill node firmware from the source code.

The node-code version may be viewed in the Server Log, and via the "About RotorHazard" item in the drop-down menu.

----------------------------------------------------------------------------

## Optional Components

### Real Time Clock

The installation of a real-time clock module allows the RotorHazard timer to maintain the correct date and time even when an internet connection is not available.  See '[doc/Real Time Clock.md](Real%20Time%20Clock.md)' for more information.

### WS2812b LED Support

Support for WS2812b LED strips (and panels) is provided by the Python library '[rpi-ws281x](https://github.com/rpi-ws281x/rpi-ws281x-python)' (which is among the libraries installed via the `sudo pip install -r requirements.txt` command.

The **LED_COUNT** value must be set in the `src/config.json` file. See the `src/config-dist.json` file for the default configuration of the 'LED' settings.  The following items may be set:

```
LED_COUNT:  Number of LED pixels in strip (or panel)
LED_ROWS:  Number of rows in a multiline LED display panel (LED_COUNT must be evenly divisible by this value; default 1)
LED_PIN:  GPIO pin connected to the pixels (default 10 uses SPI '/dev/spidev0.0')
LED_FREQ_HZ:  LED signal frequency in hertz (usually 800000)
LED_DMA:  DMA channel to use for generating signal (default 10)
LED_INVERT:  True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL:  Set to '1' for GPIOs 13, 19, 41, 45 or 53
LED_STRIP:  Strip type and color ordering (default is 'GRB')
PANEL_ROTATE:  Optional panel-rotation value (default 0)
INVERTED_PANEL_ROWS:  Optional even-index row inversion for LED panels (default false)
```
***LED_PIN*** is the GPIO number, not the hardware pin index.
If specified, the **LED_STRIP** value must be one of: 'RGB', 'RBG', 'GRB', 'GBR', 'BRG', 'BGR', 'RGBW', 'RBGW', 'GRBW',  'GBRW', 'BRGW', 'BGRW'

Running LEDs from certain GPIO pins (such as GPIO18) requires the server to be run as root. If the error message `Can't open /dev/mem: Permission denied` or `mmap() failed` appears on startup, you must run the server with `sudo` or connect LEDs to a different GPIO pin. If using a service file to start the server on boot, it may be run as root by leaving out the "User=pi" line.

### Java Support

Java enables the calculating of IMD scores, which is helpful for selecting frequency sets with less interference between VTXs. To determine if Java is installed, run the following command:

```
java -version
```
If the response is "command not found" then Java needs to be installed.

For the Raspberry Pi 3 or Pi 4, use the following command:

```
sudo apt install default-jdk-headless
```
For the Raspberry Pi Zero (or an older-model Pi), use this command:

```
sudo apt install openjdk-8-jdk-headless
```

### Server Audio

Install Bluetooth audio support:

```
sudo apt-get install bluealsa
sudo usermod -G bluetooth -a pi
```
Example `~/.asoundrc` to use Bluetooth audio by default:

```
pcm.!default {
	type plug
	slave.pcm {
		type bluealsa
		device "11:44:55:DD:EE:FF"
		profile "a2dp"
	}
}

defaults.bluealsa {
	device "00:00:00:00:00:00"
	profile "a2dp"
}
```
Install nanoTTS:

```
sudo apt-get install libasound2-dev
git clone https://github.com/gmn/nanotts
cd nanotts
make
sudo make install
```
Configure RotorHazard, `src/config.json`:

```
	"AUDIO": {
		"PLAYER": ["aplay"],
		"TTS": ["nanotts", "-p", "-i"]
	}
```

----------------------------------------------------------------------------

## Running the RotorHazard server

The following instructions will start the web server on the raspberry pi, allowing full control and configuration of the system to run races and save lap times.

### Manual Start
Open a terminal window and enter the following:

```
cd ~/RotorHazard/src
python3 -m server.server
```
The server may be stopped by hitting Ctrl-C

### Start on Boot
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
User=pi
WorkingDirectory=/home/pi/RotorHazard/src
ExecStart=/usr/bin/python3 -m server.server

[Install]
WantedBy=multi-user.target
```

Running LEDs from certain GPIO pins (such as GPIO18) requires the server to be run as root. If the error message `Can't open /dev/mem: Permission denied` or `mmap() failed` appears on startup, remove `User=pi` from this config.

Save and exit (CTRL-X, Y, ENTER).

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
### Stopping the server service
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

### Shutting down the System
A system shutdown should always be performed before unplugging the power, either by clicking on the 'Shutdown' button on the 'Settings' page, or by entering the following in a terminal:

```
sudo shutdown now
```

----------------------------------------------------------------------------

<a id="update"></a>
## Updating an existing installation

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
cp RotorHazard.old/src/config.json RotorHazard/src/
cp RotorHazard.old/src/database.db RotorHazard/src/
```
The previous installation ends up in the 'RotorHazard.old' directory, which may be deleted or moved.

For RotorHazard the minimum version of Python supported is 3.7. If your Python is older than this, you should upgrade using the steps in the "Install RotorHazard" section under "5. [Install Python](#python)."

The RotorHazard server dependencies should also be updated (be patient, this command may take a few minutes):

```
cd ~/RotorHazard/src
sudo pip install --upgrade --no-cache-dir -r requirements.txt
```

----------------------------------------------------------------------------

## Enable Port forwarding
The RotorHazard server defaults to port 5000, as this is necessary for some 3rd party integrations. While you can change the port via `HTTP_PORT` in the `config.json` file, a better approach is often to forward the web default port of 80 to 5000.

By default, HTTP uses port 80. Other values will require that the port be included as part of the URL entered into client browsers. If other web services are running on the Pi, port 80 may already be in use and reusing it will cause problems. If port 80 is used directly via `HTTP_PORT`, the server may need to be run using the *sudo* command. With the following commands, the server runs on port 5000 but the system sends the traffic from port 80 to it.

```
sudo iptables -A PREROUTING -t nat -p tcp --dport 80 -j REDIRECT --to-ports 5000
sudo iptables-save
sudo apt-get install iptables-persistent
```
After running these commands, RotorHazard will be available from both ports 80 and 5000. When available by port 80, you may leave the port off when accessing the server: `http://127.0.0.1`
<br/>

----------------------------------------------------------------------------

<a id="otheros"></a>
## Other Operating Systems

The RotorHazard server may be run on any computer with an operating system that supports Python. In these alternate configurations, one or more hardware nodes may be connected via USB -- see [doc/USB Nodes.md](USB%20Nodes.md) for more information. The server may also be run using simulated (mock) nodes.

To install the RotorHazard server on these systems:

1. If the computer does not already have Python installed, download and install Python from https://www.python.org/downloads . To check if Python is installed, open up a command prompt and enter ```python --version```

1. From the RotorHazard [Releases page on github](https://github.com/RotorHazard/RotorHazard/releases), download the "Source code (zip)" file.

1. Unzip the downloaded file into a directory (aka folder) on the computer.

1. Open up a command prompt and navigate to the ```src``` directory in the RotorHazard files (using the 'cd' command).

1. Install the RotorHazard server dependencies using the 'reqsNonPi.txt' file, using one of the commands below. (Note that this command may require administrator access to the computer, and the command may take a few minutes to finish).
  * On a Windows system the command to use will likely be:<br/>```python -m pip install -r reqsNonPi.txt```<br>

Note: If the above command fails with a message like "error: Microsoft Visual C++ 14.0 is required", the Visual C++ Build Tools may be downloaded (from [here](http://go.microsoft.com/fwlink/?LinkId=691126&fixForIE=.exe.)) and installed.<br>

  * On a Linux system the command to use will likely be:<br/>```sudo pip install -r reqsNonPi.txt```


To run the RotorHazard server on these systems:

1. Open up a command prompt and navigate to the ```src``` directory in the RotorHazard files (if not already there).

1. Enter: ```python3 -m server.server```

1. If the server starts up properly, you should see various log messages, including one like this:

    ```
    Running http server at port 5000
    ```

1. The server may be stopped by hitting Ctrl-C

If hardware nodes are connected via USB, they will need to be configured in the "SERIAL_PORTS" section in the "src/server/config.json" configuration file (see [doc/USB Nodes.md](USB%20Nodes.md) for details).

If no hardware nodes are configured, the server will operate using simulated (mock) nodes. In this mode the web-GUI interface may be explored and tested.

To view the web-GUI interface, open up a web browser and enter into the address bar: ```localhost:5000``` (If the HTTP_PORT value in the configuration has been changed then use that value instead of 5000). If the server is running then the RotorHazard main page should appear. Note that pages reserved for the race director (Admin/Settings) are password protected with the username and password specified in the configuration.
<br/>

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

If the FILELOG_LEVEL value is not NONE then the server will generate log files in the `src/logs` directory. A new log file is created each time the server starts, with each file having a unique name based on the current date and time (i.e., "rh_20200621_181239.log"). Setting FILELOG_LEVEL to DEBUG will result in more detailed log messages being stored in the log file, which can be useful when debugging problems.

The FILELOG_NUM_KEEP value is the number of log files to keep; the rest will be deleted (oldest first).

The CONSOLE_STREAM value may be "stdout" or "stderr".

If the SYSLOG_LEVEL value is not NONE then the server will send log messages to the logging utility built into the host operating system.

The current Server Log may be displayed via the "View Server Log" item in the drop-down menu. The displayed log is "live" in that it will update as new messages are generated. The log can be displayed in a separate window by clicking on the "View Server Log" menu item with the right-mouse button and selecting the "Open Link in New Window" (or similar) option.

Clicking on the "Select Text" button will select all the displayed log text, which may then be copied and pasted. Clicking on the "Download Logs" button will create and download a '.zip' archive file containing all available log files and the current configuration and database files. The '.zip' archive file can also be generated by running the server with the following command:  `python3 -m server.server --ziplogs`

**When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended.**

When troubleshooting, another place to check for error messages is the "/var/log/syslog" file, which may be viewed with a command like: `tail -100 /var/log/syslog`


<br/>

-----------------------------

See Also:<br/>
[doc/Hardware Setup.md](Hardware%20Setup.md)<br/>
[doc/USB Nodes.md](USB%20Nodes.md)<br/>
[doc/User Guide.md](User%20Guide.md)<br/>
[Build Resources (PCB, etc)](../resources/README.md)
