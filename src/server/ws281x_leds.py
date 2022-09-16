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
        logger.info('LED: selecting library "rpi_ws281x"')
    except ImportError:
        pixelModule = importlib.import_module('neopixel')
        Pixel = getattr(pixelModule, 'Adafruit_NeoPixel')
        logger.info('LED: selecting library "neopixel" (older)')

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

    logger.info('LED: hardware GPIO enabled, count={0}, pin={1}, freqHz={2}, dma={3}, invert={4}, chan={5}, strip={6}/{7}'.format(config['LED_COUNT'], config['LED_PIN'], config['LED_FREQ_HZ'], config['LED_DMA'], config['LED_INVERT'], config['LED_CHANNEL'], led_strip_config, led_strip))
    return Pixel(config['LED_COUNT'], config['LED_GPIO'], config['LED_FREQ_HZ'], config['LED_DMA'], config['LED_INVERT'], brightness, config['LED_CHANNEL'], led_strip)
