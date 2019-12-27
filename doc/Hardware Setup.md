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

### Additional Sensors
Sensors (such as BME280 and INA219) may be attached to the I2C bus and power pins. See the '..._sensor.py' files in the "src/interface" directory for implementation examples. The sensors need to be specified in the "src/server/config.json" file -- in the sample configuration below, a BME280 sensor is configured at I2C address 0x76 (as "Climate") and INA219 sensors are configured at 0x40 and 0x41.
```
    "SENSORS": {
            "i2c:0x76": {
                    "name": "Climate"
            },
            "i2c:0x40": {
                    "name": "Battery",
                    "max_current": 0.1
            },
            "i2c:0x41": {
                    "name": "Pi",
                    "max_current": 2
            }
    },
```

-----------------------------

See Also:  
[doc/Software Setup.md](Software%20Setup.md)  
[doc/User Guide.md](User%20Guide.md)
