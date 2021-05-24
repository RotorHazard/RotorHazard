'''LED visual effects'''

# to use this handler, run:
#    sudo apt-get install libjpeg-dev
#    sudo pip install pillow

from server.eventmanager import Evt
from leds import setPixels
from server.led_event_manager import LEDEffect
import gevent
from PIL import Image

def showBitmap(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    bitmaps = args['bitmaps']
    if bitmaps and bitmaps is not None:
        for bitmap in bitmaps:
            img = Image.open(bitmap['image'])
            delay = bitmap['delay']

            img = img.rotate(90 * args['panelRotate'])
            img = img.resize((strip.numPixels() // args['ledRows'], args['ledRows']))

            setPixels(strip, img, args['invertedPanelRows'])
            strip.show()
            gevent.sleep(delay/1000.0)

def discover(config, *args, **kwargs):
    # state bitmaps
    IMAGE_PATH = 'server/static/image/'
    return [
    LEDEffect("bitmapRHLogo", "Image: RotorHazard", showBitmap, {
            'include': [Evt.SHUTDOWN],
            'recommended': [Evt.STARTUP]
        }, {
            'ledRows': config['LED_ROWS'],
            'panelRotate': config['PANEL_ROTATE'],
            'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
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
            'ledRows': config['LED_ROWS'],
            'panelRotate': config['PANEL_ROTATE'],
            'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
            'bitmaps': [
                {"image": IMAGE_PATH + "LEDpanel-16x16-ellipsis.png", "delay": 0}
                ],
            'time': 8
        }),
    LEDEffect("bitmapGreenArrow", "Image: Green Upward Arrow", showBitmap, {
            'include': [Evt.SHUTDOWN],
            'recommended': [Evt.RACE_START]
        }, {
            'ledRows': config['LED_ROWS'],
            'panelRotate': config['PANEL_ROTATE'],
            'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
            'bitmaps': [
                {"image": IMAGE_PATH + "LEDpanel-16x16-arrow.png", "delay": 0}
                ],
            'time': 8
        }),
    LEDEffect("bitmapRedX", "Image: Red X", showBitmap, {
            'include': [Evt.SHUTDOWN],
            'recommended': [Evt.RACE_STOP]
        }, {
            'ledRows': config['LED_ROWS'],
            'panelRotate': config['PANEL_ROTATE'],
            'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
            'bitmaps': [
                {"image": IMAGE_PATH + "LEDpanel-16x16-X.png", "delay": 0}
                ],
            'time': 8
        }),
    LEDEffect("bitmapCheckerboard", "Image: Checkerboard", showBitmap, {
            'include': [Evt.SHUTDOWN],
            'recommended': [Evt.RACE_FINISH, Evt.RACE_STOP]
        }, {
            'ledRows': config['LED_ROWS'],
            'panelRotate': config['PANEL_ROTATE'],
            'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
            'bitmaps': [
                {"image": IMAGE_PATH + "LEDpanel-16x16-checkerboard.png", "delay": 0}
                ],
            'time': 20
        })
    ]
