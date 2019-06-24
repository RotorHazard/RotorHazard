# Hardware Setup Instructions

## Parts List

### Receiver Node(s) (this list makes one node, build up to eight)
* 1 x Arduino Nano
* 1 x RX5808 module with SPI mod (modules with date code 20120322 are known to work)
* 3 x 1k ohm resistor
* 1 x 100k ohm resistor
* 26 AWG and 30 AWG silicone wire

### System Components
* 1 x Raspberry Pi3 (Pi2 users have reported issues with multiple nodes connected)
* 8 GB (minimum) Micro SD Card
* 26 AWG and 30 AWG silicone wire (for wiring to each receiver node)
* 3D printed case for housing the electronics
* 5V power supply, 3 amp minimum (or 12V power supply if onboard regulators are used)

### Additional Components
* RF shielding (see below)

### Optional Components
* Ethernet cable, 50ft plus
* Outdoor power cable, 50ft plus
* Network router
* Laptop/tablet
* ws2812b LEDs

## Hardware Setup

### RX5808 Video Receivers
Make sure your receivers support SPI. *Most RX5808 modules on sale today already arrive with SPI enabled.* If they do not, modify the RX5808 receivers to enable SPI support as follows:

Remove the shield from the RX5808, the shield is normally held on by a few spots of solder around the edges. Use some solder wick to remove the solder and free the shield from the receiver. Be careful not to damage any ground pads on the receiver. There are usually small holes around the edge you can use to help push off the shield.

Remove the following resistor:
![RX5808 spi mod](img/rx5808-new-top.jpg)

The shield should be soldered back in place after removing the resistor.

### Receiver Nodes
Complete wiring connections between each Arduino and RX5808.
![receiver node wiring](img/Receivernode.png)


### System Assembly
Complete wiring connections between each Arduino and the Raspberry Pi.

Note: be sure all Receiver Nodes and the Raspberry Pi are tied to a common ground; if not, the i2c messages can be corrupted.
![system wiring](img/D5-i2c.png)

### Add a Directional RF Shield
A directional RF shield significantly improves the system's ability to reject false passes. This allows operators to increase its sensitivity or build courses that pass more closesly to the timing gate. Construct a directional shield that leaves a line of sight open between the timer and the timing gate, but blocks or attenuates RF signals from other directions. The most popular options to accomplish this are:
* Place the system inside a metal box with one side open, such as an ammo can, paint can, metal bucket, or computer case. It is recommended to attach this case to an electrical ground on the timer.
* Dig a hole into the ground and place your case within it
* Line your system case with copper tape

### WS2812b LED Support
The pins in the green box is what were already used by the timer. The pins in the red box is where you connect the signal and ground from the ws2812b LEDs.  The LEDs will require a separate power source. See WS2812b LED support under Software Setup.
![led wiring](img/GPIO.jpg)

### BME280 Temperature Support (optional)
Attach to the I2C bus and 5V pins.

### ADS1115/ADS1015 4-port Voltage Sensor Support (optional)
The ADS11X5 sensors provide four separate analog inputs for voltage measurement. The ADS1115 has 12 bits of resolution making for very precise voltage measurements. 
Connect VDD and GND of the sensor to the race timer 5V and GND. Wire SDA and SCL of the sensor to SDA and SCL of the timer. 
A combination of resistor dividers and gain options in config.json can be used. To support up to a 6s battery, use a 22k and 3.3k resistor divider with a configured gain of 1. 
Other combinations of resistors and gains may be more suited for your application; just be sure not to surpass the voltage limit for the selected gain.

### A913 Schottky Diode for Reduntant and Hot-swappable Batteries (optional)
This addition to the RH timer is [based on an RCGroups bus tie circuit.]( https://www.rcgroups.com/forums/showthread.php?1854050-Simple-Bus-Tie-Circuit-using-Schottky-Diodes "RCGroups Bus Tie Circuit")
It allows two batteries to run the timer redundantly. When the batteries are getting low, replace one battery at a time. This hot swapping allows racing to run uninterrupted all day. 
The diode forces the more charged battery to provide the power for the timer. Use the same battery cell count.
This modification works well with the ADS1X15 sensor because both batteries can be monitored at the same time. 

-----------------------------

See Also:  
[doc/Software Setup.md](Software%20Setup.md)  
[doc/User Guide.md](User%20Guide.md)
