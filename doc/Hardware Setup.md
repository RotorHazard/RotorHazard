# Hardware Setup Instructions

See the [RotorHazard Build Resources](../resources/README.md) page for information on race-timer circuit boards and 3D-printable cases.

For general information on the Arduino-nodes version of the timer, see '[doc/Timer Build with Arduinos.md](Timer%20Build%20with%20Arduinos.md)'

### Add a Directional RF Shield
A directional RF shield significantly improves the system's ability to reject false passes. See [RF shielding](Shielding%20and%20Course%20Position.md)

### Real Time Clock
See '[doc/Real Time Clock.md](Real%20Time%20Clock.md)' for more information on installing a real-time clock module to improve how the system maintains its date and time.

### WS2812b LED Support
The pins in the green box is what were already used by the timer. The pins in the red box is where you connect the signal and ground from the ws2812b LEDs.  The LEDs will require a separate power source. See WS2812b LED support under [doc/Software Setup.md](Software%20Setup.md).

![led wiring](img/GPIO.jpg)

### Additional Sensors
Sensors (such as BME280 and INA219) may be attached to the I2C bus and power pins. See the '..._sensor.py' files in the "src/interface" directory for implementation examples. The sensors need to be specified in the "src/server/config.json" file -- in the sample configuration below, a BME280 sensor is configured at I2C address 0x76 (as "Climate") and a INA219 sensor is configured at address 0x40 (as "Battery").
```
    "SENSORS": {
            "i2c:0x76": {
                    "name": "Climate"
            },
            "i2c:0x40": {
                    "name": "Battery",
                    "max_current": 0.1
            }
    },
```
Note that BME280 and INA219 sensors require the installation of support libraries -- see [doc/Software Setup.md](Software%20Setup.md#ina219-voltagecurrent-support).

### Multiple Timers
Multiple RotorHazard timers may be connected together (i.e., for split timing and mirroring) -- see [doc/Cluster.md](Cluster.md).

-----------------------------

See Also:<br/>
[doc/USB Nodes.md](USB%20Nodes.md)<br/>
[doc/Software Setup.md](Software%20Setup.md)<br/>
[doc/User Guide.md](User%20Guide.md)<br/>
[Build Resources (PCB, etc)](../resources/README.md)
