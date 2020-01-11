'''
Renders bitmaps to LEDs.

Example config:
    "LED": {
        "HANDLER": "bitmap",
        "BITMAPS": {
            "staging": [
                {"image": "static/image/LEDpanel-status-staging.png", "delay": 0}
            ],
            "start": [
                {"image": "static/image/LEDpanel-status-start.png", "delay": 0}
            ],
            "stop": [
                {"image": "static/image/LEDpanel-status-stop.png", "delay": 0}
            ],
            "finished": [
                {"image": "static/image/LEDpanel-status-finished.png", "delay": 0}
            ]
        },
        "LED_COUNT": 64,

Images are 8x8 = 64
'''
from led_handler import Color
import gevent
import cv2
import numpy as np

class BitmapLEDHandler:
    def __init__(self, strip, config):
        self.strip = strip
        self.config = config

    def __getattr__(self, name):
        def render(*args, **kwargs):
            bitmaps = self.config.get(name)
            if bitmaps is not None:
                for bitmap in bitmaps:
                    img = cv2.imread(bitmap['image']) # BGR
                    delay = bitmap['delay']

                    rotated = np.rot90(img, self.config['PANEL_ROTATE'])

                    self.setPixels(rotated)
                    self.strip.show()
                    gevent.sleep(delay/1000.0)
        return render

    def setPixels(self, img):
        pos = 0
        for row in range(0, img.shape[0]):
            for col in range(0, img.shape[1]):
                if pos == self.strip.numPixels():
                    return

                c = col
                if self.config['INVERTED_PANEL_ROWS']:
                    if row % 2 == 0:
                        c = 15 - col

                self.strip.setPixelColor(pos, Color(img[row][c][2], img[row][c][1], img[row][c][0]))
                pos += 1

def get_led_handler(strip, config, *args, **kwargs):
    return BitmapLEDHandler(strip, config['BITMAPS'])
