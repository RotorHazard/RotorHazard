# WS2812 interface for the Raspberry Pi 5

This is a simple interface for the WS2812 LED strip for the Raspberry Pi 5.
Currently it only supports communication over the SPI interface.

This library was created for the Raspberry Pi 5 because the previous go-to library [rpi_ws281x](https://github.com/jgarff/rpi_ws281x) is not (yet?) compatible. It should work on other Raspberry Pi models as well, but this has not been tested.

Thanks to [this repository](https://github.com/mattaw/ws2812_spi_python/) for the research on the SPI communication.

## Preparation

Enable SPI on the Raspberry Pi 5:

```bash
sudo raspi-config
```

Navigate to `Interfacing Options` -> `SPI` and enable it.

Optional: add your user to the `spi` group to avoid running the script as root:

```bash
sudo adduser YOUR_USER spidev
```

## Installation

```bash
pip install rpi5-ws2812
```

## Wiring

Connect the DIN (Data In) pin of the WS2812 strip to the MOSI (Master Out Slave In) pin of the Raspberry Pi 5. The MOSI pin is pin 19 / GPIO10 on the Raspberry Pi 5.

## Usage

```python
from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver
import time

if __name__ == "__main__":

    # Initialize the WS2812 strip with 100 leds and SPI channel 0, CE0
    strip = WS2812SpiDriver(spi_bus=0, spi_device=0, led_count=100).get_strip()
    while True:
        strip.set_all_pixels(Color(255, 0, 0))
        strip.show()
        time.sleep(2)
        strip.set_all_pixels(Color(0, 255, 0))
        strip.show()
        time.sleep(2)
```

## Use this library in a docker container

To use this library in a docker container, you need to add the `--device` flag to the `docker run` command to give the container access to the SPI interface. You also need to run the container in privileged mode.

Example:

```bash
docker run --device /dev/spidev0.0 --privileged YOUR_IMAGE
```

```yaml
services:
  your_service:
    image: YOUR_IMAGE
    privileged: true
    devices:
      - /dev/spidev0.0
```
