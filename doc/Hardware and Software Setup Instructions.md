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
Note: be sure all Receiver Nodes and the Raspberry Pi are tied to a common ground; if not, the i2c messages can be corrupted, and cause other strange things to happen.
![alt text](img/D5-i2c.png)

## Software Setup
  
### Raspberry Pi
1. Start by instaling Raspbian, follow the official instructions here: https://www.raspberrypi.org/downloads/raspbian/, use 'RASPBIAN JESSIE WITH PIXEL'
2. Install Apache
 ```
 sudo apt-get install apache2 -y
 ```
 Test to make sure Apache is running by going to ```http://localhost/``` in the RPi's browser.

3. Install PHP
 ```
 sudo apt-get install php5 libapache2-mod-php5 -y
 ```

4. Install MySQL (Note: the code in this repository uses user:root and password:delta5fpv to access the database.)
 ```
 sudo apt-get install mysql-server php5-mysql -y
 ```

5. Restart Apache
 ```
 sudo service apache2 restart
 ```
 
6. Enable I2C on the Raspberry Pi
 ```
 sudo raspi-config
 ```
 Go to Advanced Options, and enable I2C

7. Install PHPMyAdmin
```
sudo apt-get install phpmyadmin
```
Select Apache2 as the server installed, answer 'YES' to the 'Configure database for PHPMyAdmin with dbconfig-common?"
It will then ask you for the password when you created the MySQL database in Step 4.  It will also ask to setup a password for PHPMyAdmin, just make it the same as MySQL

8. Setup Apache to include our PHPMyAdmin installation
```
sudo nano /etc/apache2/apache2.conf
```
At the bottom of the file add the following line:
```
Include /etc/phpmyadmin/apache.conf
```

9. Restart Apache:
```
sudo service apache2 restart
```

10. Install Python.
```
sudo apt-get install python-dev
```
and install the python drivers for the GPIO
```
sudo apt-get install python-rpi.gpio
```
11. Give permission to run scripts as sudo (be very very careful editing this file)
```
sudo nano /etc/sudoers
```
At the bottom of the file add the following:
```
www-data ALL=(root) NOPASSWD:ALL
```

12. Update just to make sure everything is in order
```
sudo apt-get update && sudo apt-get upgrade
```

13. Install the python bindings for MySQL
```
sudo apt-get install mysql-server python-mysqldb
```

### MySQL Database setup:
1. From the browser on the pi enter the following to access PHPMyAdmin:
```
http://localhost/phpmyadmin
```
This will allow you to setup the MySQL database using the easy PHPMyAdmin GUI.

2. Create a database called 'vtx'

3. Tables and columns will be created through the web interface.

### Raspberry Pi Delta5 Code

1. Copy [/src/raspberry pi code/VTX](../src/raspberry%20pi%20code/VTX) from this repo to '/home/pi/VTX/' on the Raspberry Pi

2. Copy [/src/raspberry pi code/html](/src/raspberry%20pi%20code/html) from this repo to '/var/www/html/' on the Raspberry Pi

If you don't have write permission use:
```
sudo pcmanfm
```

### Receiver Node Arduino Code:
1. Open [/src/arduino code/delta5-race-timer-node/delta5-race-timer-node.ino](/src/arduino%20code/delta5-race-timer-node/delta5-race-timer-node.ino) in the Arduino IDE.

2. Configure 'i2cSlaveAddress' and 'vtxFreq' in the setup section of the .ino.

3. Upload to each Arduino receiver node changing 'i2cSlaveAddress' and 'vtxFreq' each time.
