'''LED visual effects'''

# to use this handler, run:
#    sudo pip install pillow

from led_event_manager import LEDEvent, Color
import gevent
from PIL import Image

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


def registerHandlers(manager):
    # register state bitmaps
    manager.registerEventHandler("bitmapRHLogo", "Image: RotorHazard", showBitmap, [LEDEvent.STARTUP], {'bitmaps': [
        {"image": "static/image/LEDpanel-RotorHazard-logo.png", "delay": 0}
    ]})
    manager.registerEventHandler("bitmapOrangeSquare", "Image: Orange Staging Square", showBitmap, [LEDEvent.RACESTAGE], {'bitmaps': [
        {"image": "static/image/LEDpanel-status-staging.png", "delay": 0}
    ]})
    manager.registerEventHandler("bitmapGreenArrow", "Image: Green Upward Arrow", showBitmap, [LEDEvent.RACESTART], {'bitmaps': [
        {"image": "static/image/LEDpanel-status-start.png", "delay": 0}
    ]})
    manager.registerEventHandler("bitmapRedX", "Image: Red X", showBitmap, [LEDEvent.RACESTOP], {'bitmaps': [
        {"image": "static/image/LEDpanel-status-stop.png", "delay": 0}
    ]})
    manager.registerEventHandler("bitmapCheckerboard", "Image: Checkerboard", showBitmap, [LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {'bitmaps': [
        {"image": "static/image/LEDpanel-status-finished.png", "delay": 0}
    ]})
