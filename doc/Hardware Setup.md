# Hardware Setup Instructions

See the [RotorHazard Build Resources &#10132;&#xFE0E;](https://github.com/RotorHazard/RotorHazard/tree/main/resources/README.md) page for information on race-timer circuit boards and 3D-printable cases.

For general information on the Arduino-nodes version of the timer, see '[doc/Timer Build with Arduinos.md](Timer%20Build%20with%20Arduinos.md)'

### RX5808 Video Receivers
RotorHazard requires RX5808 modules to have SPI communication enabled in order to change channels. Some receivers arrive without this set up. If SPI is not enabled, the receivers will not listen or change channels correctly. If this happens, modify the RX5808 receivers to enable SPI support as follows:

> [!IMPORTANT]
> 
> If RotorHazard is receiving video signal input but does not appear to be responding correctly when transmitters are powered on, do this modification. 

> [!TIP]
> 
> It is safe—and generally necessary—to first install the module before knowing if this modification is needed.  

Remove the shield from the RX5808, the shield is normally held on by a few spots of solder around the edges. Use some solder wick to remove the solder and free the shield from the receiver. Be careful not to damage any ground pads on the receiver. There are usually small holes around the edge you can use to help push off the shield.

Remove the following resistor:

![RX5808 spi mod](img/rx5808-new-top.jpg)

The shield should be soldered back in place after removing the resistor.

### Add a Directional RF Shield
A directional RF shield significantly improves the system's ability to reject false passes. See [RF shielding](Shielding%20and%20Course%20Position.md)

### Real Time Clock
See '[doc/Real Time Clock.md](Real%20Time%20Clock.md)' for more information on installing a real-time clock module to improve how the system maintains its date and time.

### WS2812b LED Support

For the [S32_BPill board](../resources/S32_BPill_PCB/README.md) connect to J6 "Pi_LED" (near the middle of the board); pin 1 is ground, pin 2 is signal.

For the [6 Node STM32](../resources/6_Node_BPill_PCB/README.md) board use the 'LEDS' connector.

For the [RotorHazard PCB 1.2 board](../resources/PCB/README.md) use the LED OUT connector (beware of overloading the 5V power supply).

See [WS2812b LED Support](Software%20Setup.md#ws2812b-led-support) under [doc/Software Setup.md](Software%20Setup.md).

For direct wiring to the Pi: The pins in the green box is what were already used by the timer. The pins in the red box is where you connect the signal and ground from the ws2812b LEDs.  The LEDs will require a separate power source.

![led wiring](img/GPIO.jpg)

### Additional Sensors
Sensors (such as BME280 and INA219) may be attached to the I2C bus and power pins. See the '..._sensor.py' files in the "src/interface" directory for implementation examples. Sensors need to be added to the server configuration on the _Settings_ page in the _Environment Sensors_ panel. Type the sensor's address into the `Address` input and complete the entry (click outside or use the tab key to defocus). A new `Sensor` section will be added. Add multiple items if desired, or clear the `Address` to remove. You can similarly add and remove key/value pairs to configure individual sensor types. All sensors support the `name` key, but individual sensors may use other keys. For example, a battery sensor may have a `max_current` configuration key.

### Multiple Timers
Multiple RotorHazard timers may be connected together (i.e., for split timing and mirroring) -- see [doc/Cluster.md](Cluster.md).

-----------------------------

See Also:<br/>
[doc/USB Nodes.md](USB%20Nodes.md)<br/>
[doc/Software Setup.md](Software%20Setup.md)<br/>
[doc/User Guide.md](User%20Guide.md)<br/>
[Build Resources (PCB, etc) &#10132;&#xFE0E;](https://github.com/RotorHazard/RotorHazard/tree/main/resources/README.md)
