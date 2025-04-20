'''WS281x LED layer.'''

import importlib
import logging
logger = logging.getLogger(__name__)

def get_pixel_interface(config, brightness, *args, **kwargs):
    '''Returns the pixel interface.'''

    Pixel = None
    try:
        pixelModule = importlib.import_module('rpi_ws281x')
        Pixel = getattr(pixelModule, 'Adafruit_NeoPixel')
    except ImportError:
        pixelModule = importlib.import_module('neopixel')
        Pixel = getattr(pixelModule, 'Adafruit_NeoPixel')
        logger.info('LED: using library "neopixel" (older)')

    led_strip_config = config['LED_STRIP']
    if led_strip_config == 'RGB':
        led_strip = 0x00100800
    elif led_strip_config == 'RBG':
        led_strip = 0x00100008
    elif led_strip_config == 'GRB':
        led_strip = 0x00081000
    elif led_strip_config == 'GBR':
        led_strip = 0x00080010
    elif led_strip_config == 'BRG':
        led_strip = 0x00001008
    elif led_strip_config == 'BGR':
        led_strip = 0x00000810
    elif led_strip_config == 'RGBW':
        led_strip = 0x18100800
    elif led_strip_config == 'RBGW':
        led_strip = 0x18100008
    elif led_strip_config == 'GRBW':
        led_strip = 0x18081000
    elif led_strip_config == 'GBRW':
        led_strip = 0x18080010
    elif led_strip_config == 'BRGW':
        led_strip = 0x18001008
    elif led_strip_config == 'BGRW':
        led_strip = 0x18000810

    else:
        logger.info('LED: disabled (Invalid LED_STRIP value: {0})'.format(led_strip_config))
        return None

    try:
        # if Raspberry Pi 5 then don't attempt to initialize 'rpi_ws281x' (to avoid "segmentation fault" messages)
        _is_pi5_flag = False
        try:
            with open("/proc/device-tree/model", 'r') as fileHnd:
                _modelStr = fileHnd.read()
            if _modelStr.startswith("Raspberry Pi ") and int(_modelStr[13:15]) == 5:
                _is_pi5_flag = True
        except:
            pass
        if _is_pi5_flag:
            raise RuntimeError("Not attempting to initialize 'rpi_ws281x' because Raspberry Pi 5 detected")

        pixel_obj = Pixel(config['LED_COUNT'], config['LED_GPIO'], config['LED_FREQ_HZ'], config['LED_DMA'], \
                          config['LED_INVERT'], int(brightness), config['LED_CHANNEL'], led_strip)
        pixel_obj.begin()
        pixel_obj.begin = lambda : None  # don't allow 'begin()' to be invoked again
        logger.info('LED: selecting library "rpi_ws281x"')
        logger.info('LED: hardware GPIO enabled, count={0}, pin={1}, freqHz={2}, dma={3}, invert={4}, chan={5}, strip={6}/{7}'. \
                format(config['LED_COUNT'], config['LED_GPIO'], config['LED_FREQ_HZ'], config['LED_DMA'], \
                       config['LED_INVERT'], config['LED_CHANNEL'], led_strip_config, led_strip))
        return pixel_obj

    except Exception as ex:
        logger.debug("Result of attempting to initialize 'rpi_ws281x' library:  '{}'".format(ex))

    try:
        import rpi5_ws2812  #pylint: disable=import-error
        from rpi5_ws2812.ws2812 import WS2812SpiDriver as rpi5_WS2812SpiDriver  #pylint: disable=import-error
        from rpi5_ws2812.ws2812 import Color as rpi5_ws2812_Color  #pylint: disable=import-error
        rpi5_strip = rpi5_WS2812SpiDriver(spi_bus=0, spi_device=0, led_count=config['LED_COUNT']).get_strip()

        # emulate 'rpi_ws281x' functions:

        rpi5_strip.begin = lambda : None
        rpi5_strip.numPixels = rpi5_strip.num_pixels
        rpi5_strip.setPixelColor = lambda i, val : rpi5_strip.set_pixel_color(i,
                                       rpi5_ws2812_Color((val >> 16), ((val >> 8) & 255), (val & 255)))
        rpi5_strip.setBrightness = lambda val : rpi5_strip.set_brightness(val / 100.0)
        rpi5_strip.getBrightness = lambda : rpi5_strip.get_brightness * 100.0

        def _get_rpi5_pix_clr(i):
            val = rpi5_strip._pixels[i]
            return (val.r << 16) | (val.g << 8) | val.b

        rpi5_strip.getPixelColor = lambda i : _get_rpi5_pix_clr(i)

        rpi5_strip.setBrightness(int(brightness))  # set initial configured brightness

        logger.info("LED: using 'rpi5-ws2812' library instead of 'rpi_ws281x' (only GPIO10 supported)")
        logger.info('LED: hardware GPIO enabled, count={0}'.format(config['LED_COUNT']))
        return rpi5_strip
    except:
        logger.exception("Error attempting to use 'rpi5-ws2812' library")
        return None
