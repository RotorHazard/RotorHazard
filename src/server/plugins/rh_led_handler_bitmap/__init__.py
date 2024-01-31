'''LED visual effects'''

# To use this LED-panel plugin see:
#   https://github.com/RotorHazard/RotorHazard/blob/main/doc/Software%20Setup.md#led-panel-support

import logging
import Config
from eventmanager import Evt
from led_event_manager import LEDEffect, Color, effect_delay
import gevent

logger = logging.getLogger(__name__)

try:
    from PIL import Image
except ModuleNotFoundError as ex:
    logger.debug(str(ex) + " ('pillow' module needed to use '" + __name__ + "')")
    raise ModuleNotFoundError("'pillow' module not found") from ex

def showBitmap(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    def setPixels(img, panel_w):
        pos = 0
        for row in range(0, img.height):
            for col in range(0, img.width):
                if pos >= strip.numPixels():
                    return

                c = col
                if Config.LED['INVERTED_PANEL_ROWS']:
                    if row % 2 == 0:
                        c = (panel_w - 1) - col

                px = img.getpixel((c, row))
                strip.setPixelColor(pos, Color(px[0], px[1], px[2]))
                pos += 1

    bitmaps = args['bitmaps']
    if bitmaps and bitmaps is not None:
        for bitmap in bitmaps:
            img = Image.open(bitmap['image'])
            delay = bitmap['delay']

            panel_w = Config.LED['LED_COUNT'] // Config.LED['LED_ROWS']
            panel_h = Config.LED['LED_ROWS']

            if Config.LED['PANEL_ROTATE'] % 2:
                output_w = panel_h
                output_h = panel_w
            else:
                output_w = panel_w
                output_h = panel_h

            size = img.size

            ratio_w = output_w / size[0]
            ratio_h = output_h / size[1]

            ratio = min(ratio_w, ratio_h)

            img = img.resize((int(size[0]*ratio), int(size[1]*ratio)))

            output_img = Image.new(img.mode, (output_w, output_h))
            size = img.size
            pad_left = int((output_w - size[0]) / 2) 
            pad_top = int((output_h - size[1]) / 2)
            output_img.paste(img, (pad_left, pad_top))
            output_img = output_img.rotate(90 * Config.LED['PANEL_ROTATE'], expand=True)

            setPixels(output_img, panel_w)
            strip.show()
            effect_delay(delay, args.get('_effect'))

def register_handlers(args):
    for led_effect in [
        LEDEffect("Image: RotorHazard", showBitmap, {
                'recommended': [Evt.STARTUP]
            }, {
                'bitmaps': [
                    {'image': 'static/image/LEDpanel-16x16-RotorHazard.png', 'delay': 0}
                    ],
                'time': 60
            },
            name='bitmapRHLogo',
        ),
        LEDEffect("Image: Orange Ellipsis", showBitmap, {
                'recommended': [Evt.RACE_STAGE]
            }, {
                'bitmaps': [
                    {'image': 'static/image/LEDpanel-16x16-ellipsis.png', 'delay': 0}
                    ],
                'time': 8
            },
            name='bitmapOrangeEllipsis',
        ),
        LEDEffect("Image: Green Upward Arrow", showBitmap, {
                'recommended': [Evt.RACE_START]
            }, {
                'bitmaps': [
                    {'image': 'static/image/LEDpanel-16x16-arrow.png', 'delay': 0}
                    ],
                'time': 8
            },
            name='bitmapGreenArrow',
        ),
        LEDEffect("Image: Red X", showBitmap, {
                'recommended': [Evt.RACE_STOP]
            }, {
                'bitmaps': [
                    {'image': 'static/image/LEDpanel-16x16-X.png', 'delay': 0}
                    ],
                'time': 8
            },
            name='bitmapRedX',
        ),
        LEDEffect("Image: Checkerboard", showBitmap, {
                'recommended': [Evt.RACE_FINISH, Evt.RACE_STOP]
            }, {
                'bitmaps': [
                    {'image': 'static/image/LEDpanel-16x16-checkerboard.png', 'delay': 0}
                    ],
            'time': 20
            },
            name='bitmapCheckerboard',
        )
    ]:
        args['register_fn'](led_effect)

def initialize(rhapi):
    rhapi.events.on(Evt.LED_INITIALIZE, register_handlers)

