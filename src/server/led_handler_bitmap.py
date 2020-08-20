'''LED visual effects'''

# to use this handler, run:
#    sudo apt-get install libjpeg-dev
#    sudo pip install pillow

import Config
from eventmanager import Evt
from led_event_manager import LEDEffect, LEDEvent, Color
import gevent
from PIL import Image

def showBitmap(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    def setPixels(img):
        pos = 0
        for row in range(0, img.height):
            for col in range(0, img.width):
                if pos >= strip.numPixels():
                    return

                c = col
                if Config.LED['INVERTED_PANEL_ROWS']:
                    if row % 2 == 0:
                        c = 15 - col

                px = img.getpixel((c, row))
                strip.setPixelColor(pos, Color(px[0], px[1], px[2]))
                pos += 1

    bitmaps = args['bitmaps']
    if bitmaps and bitmaps is not None:
        for bitmap in bitmaps:
            img = Image.open(bitmap['image'])
            delay = bitmap['delay']

            img = img.rotate(90 * Config.LED['PANEL_ROTATE'])

            setPixels(img)
            strip.show()
            gevent.sleep(delay/1000.0)


def discover(*args, **kwargs):
    # state bitmaps
    return [
    LEDEffect("bitmapRHLogo", "Image: RotorHazard", showBitmap, [Evt.STARTUP, Evt.RACE_STAGE, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.SHUTDOWN], {'bitmaps': [
        {"image": "static/image/LEDpanel-16x16-RotorHazard.png", "delay": 0}
        ]}),
    LEDEffect("bitmapOrangeSquare", "Image: Orange Pause Icon", showBitmap, [Evt.RACE_STAGE], {'bitmaps': [
        {"image": "static/image/LEDpanel-16x16-pause.png", "delay": 0}
        ]}),
    LEDEffect("bitmapGreenArrow", "Image: Green Upward Arrow", showBitmap, [Evt.RACE_START], {'bitmaps': [
        {"image": "static/image/LEDpanel-16x16-arrow.png", "delay": 0}
        ]}),
    LEDEffect("bitmapRedX", "Image: Red X", showBitmap, [Evt.RACE_STOP], {'bitmaps': [
        {"image": "static/image/LEDpanel-16x16-X.png", "delay": 0}
        ]}),
    LEDEffect("bitmapCheckerboard", "Image: Checkerboard", showBitmap, [Evt.RACE_FINISH, Evt.RACE_STOP], {'bitmaps': [
        {"image": "static/image/LEDpanel-16x16-checkerboard.png", "delay": 0}
        ]})
    ]
