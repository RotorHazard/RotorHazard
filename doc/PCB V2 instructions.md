# PCB V2 Setup Instructions

## Parts List for an 8 node system

* PCBs v2.0 - 4 node board; link 2 PCBs to get an 8 node system (pack of 10) - https://www.seeedstudio.com/Delta-5-Race-Timer-v2-0-g-1048578
* 1 * Raspberry Pi 3 Model B ARM Cortex-A53 CPU 1.2GHz 64-Bit Quad-Core 1GB RAM 10 Times B+ - https://www.banggood.com/Raspberry-Pi-3-Model-B-ARM-Cortex-A53-CPU-1_2GHz-64-Bit-Quad-Core-1GB-RAM-10-Times-B-p-1041862.html
* 8 * Arduino Nano (you need 2 packs of 5) - https://www.banggood.com/5Pcs-ATmega328P-Arduino-Compatible-Nano-V3-Improved-Version-No-Cable-p-971293.html
* 8 * RX5808 Receiver Modules - https://www.banggood.com/FPV-5_8G-Wireless-Audio-Video-Receiving-Module-RX5808-p-84775.html
* 8 * 100k Ohm Resistors - E-Projects 10EP512100K 100k Ohm Resistors, 1/2 W, 5% (Pack of 10) - http://a.co/1uJiJUd
* 24 * 1k Ohm Resistors - 1K Ohm, 1/4 Watt, 5%, Carbon Film Resistors (pack of 250) - http://a.co/3LwKV7i
* 1 * Pololu 5V, 2.5A Step-Down Voltage Regulator D24V25F5 by Pololu - https://www.pololu.com/product/2850
* 1 * Pololu 3.3V, 2.5A Step-Down Voltage Regulator D24V25F3 - https://www.pololu.com/product/2849
* 1 * XT60 Male Plug 12AWG 10cm With Wire (pack of 2) https://www.banggood.com/2-X-XT60-Male-Plug-12AWG-10cm-With-Wire-p-987484.html
* 10 Pcs 40 Pin 2.54mm Single Row Male Pin Header Strip For Arduino -
https://eu.banggood.com/Wholesale-Warehouse-10-Pcs-40-Pin-2_54mm-Single-Row-Male-Pin-Header-Strip-For-Arduino-wp-Eu-918427.html
* 10pcs 40Pin 2.54mm Female Header Connector Socket For DIY Arduino - https://www.banggood.com/10pcs-40Pin-2_54mm-Female-Header-Connector-Socket-For-DIY-Arduino-p-945516.html
* 10 female to female jumper cables - https://www.banggood.com/3-IN-1-120pcs-10cm-Male-To-Female-Female-To-Female-Male-To-Male-Jumper-Cable-Dupont-Wire-For-Arduino-p-1054670.html
* Don't forget to buy a micro SD card for the Raspberry PI

## Hardware Setup

### RX5808 Video Receivers
Modify the rx5808 receivers to use SPI.

Remove the shield from the rx5808, the shield is normally held on by a few spots of solder around the edges. Use some solder wick to remove the solder and free the shield from the receiver. Be careful not to damage any ground pads on the receiver. There are usually small holes around the edge you can use to help push off the shield.

Remove the following resistor:
![rx5808 spi mod](img/rx5808-new-top-min.pg)

The shield should be soldered back in place after removing the resistor.

Note: the rx5808 bought via the above Banggood link already has the resistor removed. It doesn't hurt to double check a few.

### Step by step instructions

This is what we'll work towards. It is a 4 node set-up, but is easy to extend (with almost the exact same steps for an 8 node set-up).
![End result](img/pcbv2/0_end_result-min.jpg)

PCB V2 front
![Front](img/pcbv2/1_front-min.jpg)

PCB V2 back
![Back](img/pcbv2/2_back-min.jpg)

Cut the female pin headers (to hold the Arduinos) to the appropriate length and solder them to the PCB
![Adding female pin headers](img/pcbv2/3_female_pin_headers-min.jpg)

Adding resistors, the PCB indicates which goes where
![Added resistors](img/pcbv2/5_resistors_ready-min.jpg)

Checking where the rx5808 module already has the spi mod (as described above)
![Check the module](img/pcbv2/6_checking_module-min.jpg)

Holding the rx5808 temporarily in place for easy soldering.
![How to temporarily fix the rx5808](img/pcbv2/7_holding_rx5808_in_place-min.jpg)

First rx5808 in place
![1 rx5808](img/pcbv2/8_first_rx5808_done-min.jpg)

All rx5808 in place, verified all contacts with multimeter
![verify contacts with multi meter](img/pcbv2/10_all_rx5808_once_again-min.jpg)

The back side at this stage
![back side at this stage](img/pcbv2/11_back_with_solder-min.jpg)

Adding male pin headers for connecting the Raspberry Pi, a second PCB, as well as for the polulus
![add some male pin headers](img/pcbv2/12_male_pin_headers-min.jpg)

Adding the XT60
![add xt60](img/pcbv2/13_xt60-min.jpg)

Adding a 3.3V polulu (left) for the rx5808 and a 5V polulu (right) for powering the Arduinos and Raspberry Pi. Note: in an 8-node setup the second PCB does not need polulus.
![add polulus](img/pcbv2/14_polulu-min.jpg)

Close-up of how the polulus are floating above the resistors.
![polulu close-up](img/pcbv2/15_polulu_close_up-min.jpg)

Added jumpers to power the Arduinos (remove jumpers if you want to update the software on the Arduino)
![added jumpers](img/pcbv2/16_jumpers-min.jpg)

How jumpers are made :D
![how the jumpers were made](img/pcbv2/17_how_jumpers_are_made-min.jpg)

Plugging in the Arduinos. 
![arduinos plugged in](img/pcbv2/18_arduinos-min.jpg)

Connections between Raspberry PI and PCB (check the [wiring diagram](https://docs.microsoft.com/en-us/windows/iot-core/learn-about-hardware/pinmappings/pinmappingsrpi#gpio-pins) to be sure, you need 5v, ground, sda and sdl). ![connections between rpi and pcb](img/pcbv2/19_connections-min.jpg)

Follow the software instructions on [https://github.com/RotorHazard/RotorHazard/blob/master/doc/Software%20Setup.md](https://github.com/RotorHazard/RotorHazard/blob/master/doc/Software%20Setup.md)

![](img/pcbv2/20_eth0-min.jpg)

To get from the 4-node to the 8-node system, repeat all the steps (except the polulus) on a second PCB. Then connect the six pin headers on the side of the first PCB to the corresponding pin headers on the second PCB.

### Add a Directional RF Shield
A directional RF shield significantly improves the system's ability to reject false passes. This allows operators to increase its sensitivity or build courses that pass more closesly to the timing gate. Construct a directional shield that leaves a line of sight open between the timer and the timing gate, but blocks or attenuates RF signals from other directions. The most popular options to accomplish this are:
* Place the system inside a metal box with one side open, such as an ammo can, paint can, metal bucket, or computer case. It is recommended to attach this case to an electrical ground on the timer.
* Dig a hole into the ground and place your case within it
* Line your system case with copper tape

### WS2812b LED Support (optional)
The pins in the green box is what were already used by the timer. The pins in the red box is where you connect the signal and ground from the ws2812b LEDs.  The LEDs will require a separate power source. See WS2812b LED support under Software Setup.
![led wiring](img/GPIO.jpg)

### BME280 Temperature support (optional)
Attach to the I2C bus and 5V pins.

