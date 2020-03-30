'''LED visual effects'''

# to use this handler, run:
#    sudo apt-get install libjpeg-dev
#    sudo pip install pillow

import Config
from eventmanager import Evt
from led_event_manager import LEDEvent, Color
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


def registerEffects(manager):
    # register state bitmaps
    manager.registerEffect("bitmapRHLogo", "Image: RotorHazard", showBitmap, [Evt.STARTUP, Evt.RACESTAGE, Evt.RACESTART, Evt.RACEFINISH, Evt.RACESTOP, Evt.SHUTDOWN], {'bitmaps': [
        {"image": "static/image/LEDpanel-16x16-RotorHazard.png", "delay": 0}
        ]})
    manager.registerEffect("bitmapOrangeSquare", "Image: Orange Pause Icon", showBitmap, [Evt.RACESTAGE], {'bitmaps': [
        {"image": "static/image/LEDpanel-16x16-pause.png", "delay": 0}
        ]})
    manager.registerEffect("bitmapGreenArrow", "Image: Green Upward Arrow", showBitmap, [Evt.RACESTART], {'bitmaps': [
        {"image": "static/image/LEDpanel-16x16-arrow.png", "delay": 0}
        ]})
    manager.registerEffect("bitmapRedX", "Image: Red X", showBitmap, [Evt.RACESTOP], {'bitmaps': [
        {"image": "static/image/LEDpanel-16x16-X.png", "delay": 0}
        ]})
    manager.registerEffect("bitmapCheckerboard", "Image: Checkerboard", showBitmap, [Evt.RACEFINISH, Evt.RACESTOP], {'bitmaps': [
        {"image": "static/image/LEDpanel-16x16-checkerboard.png", "delay": 0}
        ]})
