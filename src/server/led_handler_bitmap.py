'''LED visual effects'''

# to use this handler, run:
#    sudo pip install pillow

import gevent
from PIL import Image
from led_handler_generic import Color

def showBitmap(strip, config, args):
    def setPixels(img):
        pos = 0
        for row in range(0, img.height):
            for col in range(0, img.width):
                if pos >= strip.numPixels():
                    return

                c = col
                if config['INVERTED_PANEL_ROWS']:
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

            img = img.rotate(90 * config['PANEL_ROTATE'])

            setPixels(img)
            strip.show()
            gevent.sleep(delay/1000.0)


def registerHandlers(handler):
    # register state bitmaps
    handler.registerEventHandler("startupBitmap", showBitmap, ["startup"], {'bitmaps': [
        {"image": "static/image/LEDpanel-RotorHazard-logo.png", "delay": 0}
    ]})
    handler.registerEventHandler("stagingBitmap", showBitmap, ["raceStaging"], {'bitmaps': [
        {"image": "static/image/LEDpanel-status-staging.png", "delay": 0}
    ]})
    handler.registerEventHandler("startBitmap", showBitmap, ["raceStarted"], {'bitmaps': [
        {"image": "static/image/LEDpanel-status-start.png", "delay": 0}
    ]})
    handler.registerEventHandler("stoppedBitmap", showBitmap, ["raceStopped"], {'bitmaps': [
        {"image": "static/image/LEDpanel-status-stop.png", "delay": 0}
    ]})
    handler.registerEventHandler("finishedBitmap", showBitmap, ["raceFinished"], {'bitmaps': [
        {"image": "static/image/LEDpanel-status-finished.png", "delay": 0}
    ]})
