'''WS281x LED layer.'''

from rpi_ws281x import Adafruit_NeoPixel

def get_pixel_interface(config, *args, **kwargs):
    '''Returns the pixel interface.'''
    led_strip_config = config['LED_STRIP']
    if led_strip_config == 'RGB':
        led_strip = 0x00100800
    elif led_strip_config == 'RBG':
        led_strip = 0x00100008
    elif led_strip_config == 'GRB':
        led_strip = 0x000810000
    elif led_strip_config == 'GBR':
        led_strip = 0x00080010
    elif led_strip_config == 'BRG':
        led_strip = 0x00001008
    elif led_strip_config == 'BGR':
        led_strip = 0x00000810
    else:
        print 'LED: disabled (Invalid LED_STRIP value: {0})'.format(led_strip_config)
        return None

    print('LED: hardware GPIO enabled')
    return Adafruit_NeoPixel(config['LED_COUNT'], config['LED_PIN'], config['LED_FREQ_HZ'], config['LED_DMA'], config['LED_INVERT'], config['LED_BRIGHTNESS'], config['LED_CHANNEL'], led_strip)
