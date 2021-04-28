'''LED visual effects'''

# to use this handler, run:
#    sudo apt-get install libjpeg-dev
#    sudo pip install pillow

from server import Config
from server.eventmanager import Evt
from server.led_event_manager import LEDEffect, Color
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
            img = img.resize((Config.LED['LED_COUNT'] // Config.LED['LED_ROWS'], Config.LED['LED_ROWS']))

            setPixels(img)
            strip.show()
            gevent.sleep(delay/1000.0)

def discover(*args, **kwargs):
    # state bitmaps
    IMAGE_PATH = 'server/static/image/'
    return [
    LEDEffect("bitmapRHLogo", "Image: RotorHazard", showBitmap, {
            'include': [Evt.SHUTDOWN],
            'recommended': [Evt.STARTUP]
        }, {
            'bitmaps': [
                {"image": IMAGE_PATH + "LEDpanel-16x16-RotorHazard.png", "delay": 0}
                ],
            'time': 60
            },
        ),
    LEDEffect("bitmapOrangeEllipsis", "Image: Orange Ellipsis", showBitmap, {
            'include': [Evt.SHUTDOWN],
            'recommended': [Evt.RACE_STAGE]
        }, {
            'bitmaps': [
                {"image": IMAGE_PATH + "LEDpanel-16x16-ellipsis.png", "delay": 0}
                ],
            'time': 8
        }),
    LEDEffect("bitmapGreenArrow", "Image: Green Upward Arrow", showBitmap, {
            'include': [Evt.SHUTDOWN],
            'recommended': [Evt.RACE_START]
        }, {
            'bitmaps': [
                {"image": IMAGE_PATH + "LEDpanel-16x16-arrow.png", "delay": 0}
                ],
            'time': 8
        }),
    LEDEffect("bitmapRedX", "Image: Red X", showBitmap, {
            'include': [Evt.SHUTDOWN],
            'recommended': [Evt.RACE_STOP]
        }, {
            'bitmaps': [
                {"image": IMAGE_PATH + "LEDpanel-16x16-X.png", "delay": 0}
                ],
            'time': 8
        }),
    LEDEffect("bitmapCheckerboard", "Image: Checkerboard", showBitmap, {
            'include': [Evt.SHUTDOWN],
            'recommended': [Evt.RACE_FINISH, Evt.RACE_STOP]
        }, {
            'bitmaps': [
                {"image": IMAGE_PATH + "LEDpanel-16x16-checkerboard.png", "delay": 0}
                ],
        'time': 20
        })
    ]
