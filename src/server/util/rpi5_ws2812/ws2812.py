from abc import ABC, abstractmethod
from collections import namedtuple

import numpy as np
from spidev import SpiDev

Color = namedtuple("Color", ["r", "g", "b"])


class Strip:
    """
    A class to control a WS2812 LED strip.
    """

    def __init__(self, backend: "WS2812StripDriver"):
        self._led_count = backend.get_led_count()
        self._brightness = 1.0
        self._pixels: list[Color] = [Color(0, 0, 0)] * self._led_count
        self._backend = backend

    def set_pixel_color(self, i: int, color: Color) -> None:
        """
        Set the color of a single pixel in the buffer. It is not written to the LED strip until show() is called.
        :param i: The index of the pixel
        :param color: The color to set the pixel to
        """
        self._pixels[i] = color

    def show(self) -> None:
        """
        Write the current pixel colors to the LED strip.
        """
        buffer = np.array(
            [
                np.array([pixel.g * self._brightness, pixel.r * self._brightness, pixel.b * self._brightness])
                for pixel in self._pixels
            ],
            dtype=np.uint8,
        )
        self._backend.write(buffer)

    def clear(self) -> None:
        """
        Clear the LED strip and the buffer by setting all pixels to off.
        """
        self._pixels = [Color(0, 0, 0)] * self._led_count
        self._backend.clear()

    def set_brightness(self, brightness: float) -> None:
        """
        Set the brightness of the LED strip. The brightness is a float between 0.0 and 1.0.
        """
        self._brightness = max(min(brightness, 1.0), 0.0)

    def num_pixels(self) -> int:
        """
        Get the number of pixels in the LED strip.
        :return: The number of pixels.
        """
        return self._led_count

    def get_brightness(self) -> float:
        """
        Get the current brightness of the LED strip.
        :return: The brightness as a float between 0.0 and 1.0."""
        return self._brightness

    def set_all_pixels(self, color: Color) -> None:
        """
        Set all pixels to the same color. The colors are not written to the LED strip until show() is called.
        :param color: The color to set all pixels to.
        """
        self._pixels = [color] * self._led_count


class WS2812StripDriver(ABC):
    """
    Abstract base class for drivers
    """

    @abstractmethod
    def write(self, colors: np.ndarray) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def get_led_count(self) -> int:
        pass

    def get_strip(self) -> Strip:
        return Strip(self)


class WS2812SpiDriver(WS2812StripDriver):
    """
    Driver for WS2812 LED strips using the SPI interface on the Raspberry Pi.
    """

    # WS2812 timings. Thanks to https://github.com/mattaw/ws2812_spi_python
    LED_ZERO: int = 0b1100_0000
    LED_ONE: int = 0b1111_1100
    PREAMBLE: int = 42

    def __init__(self, spi_bus: int, spi_device: int, led_count: int):
        self._device = SpiDev()
        self._device.open(spi_bus, spi_device)

        self._device.max_speed_hz = 6_500_000
        self._device.mode = 0b00
        self._device.lsbfirst = False

        self._clear_buffer = np.zeros(WS2812SpiDriver.PREAMBLE + led_count * 24, dtype=np.uint8)
        self._clear_buffer[WS2812SpiDriver.PREAMBLE :] = np.full(
            led_count * 24, WS2812SpiDriver.LED_ZERO, dtype=np.uint8
        )

        self._buffer = np.zeros(WS2812SpiDriver.PREAMBLE + led_count * 24, dtype=np.uint8)

        self._led_count = led_count

    def write(self, buffer: np.ndarray) -> None:
        """
        Write colors to the LED strip
        :param colors: A 2D numpy array of shape (num_leds, 3) where the last dimension is the GRB values
        """
        flattened_colors = buffer.ravel()
        color_bits = np.unpackbits(flattened_colors)
        self._buffer[WS2812SpiDriver.PREAMBLE :] = np.where(
            color_bits == 1, WS2812SpiDriver.LED_ONE, WS2812SpiDriver.LED_ZERO
        )
        self._device.writebytes2(self._buffer)

    def clear(self) -> None:
        """
        Reset all LEDs to off"""
        self._device.writebytes2(self._clear_buffer)

    def get_led_count(self) -> int:
        return self._led_count
