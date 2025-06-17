# Timer Build with Arduinos

## Parts List

### Receiver Node(s) (this list makes one node, build up to eight)
* 1 x [Arduino Nano](https://www.ebay.com/sch/i.html?_nkw=Arduino+Nano+V3.0+16M+5V+ATmega328P)
* 1 x [RX5808 module](https://www.banggood.com/search/rx5808-module.html) with SPI mod (see below)
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
* [RF shielding](Shielding%20and%20Course%20Position.md)

### Optional Components
* Ethernet cable, 50ft plus
* Outdoor power cable, 50ft plus
* Network router
* Laptop/tablet
* ws2812b LEDs

## Hardware Setup

### RX5808 Video Receivers
RX5808 modules may need a small hardware modification in order to change channels. See [General Hardware Setup](Hardware%20Setup.md#rx5808-video-receivers) for more information.

### Receiver Nodes
Complete wiring connections between each Arduino and RX5808.
![receiver node wiring](img/Receivernode.png)

Note: A simple receiver node may also be constructed and attached via USB -- see [doc/USB Nodes.md](USB%20Nodes.md).

### System Assembly
Complete wiring connections between each Arduino and the Raspberry Pi.

Note: be sure all Receiver Nodes and the Raspberry Pi are tied to a common ground; if not, the i2c messages can be corrupted.
![system wiring](img/D5-i2c.png)

-----------------------------

See Also:<br/>
[doc/Hardware Setup.md](Hardware%20Setup.md)<br/>
[doc/USB Nodes.md](USB%20Nodes.md)<br/>
[doc/Software Setup.md](Software%20Setup.md)<br/>
[doc/User Guide.md](User%20Guide.md)<br/>
[Build Resources (PCB, etc) &#10132;&#xFE0E;](https://github.com/RotorHazard/RotorHazard/tree/main/resources)
