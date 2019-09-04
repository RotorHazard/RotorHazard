'''
Renders bitmaps to LEDs.

Example config:
    "LED": {
        "HANDLER": "bitmap",
        "BITMAPS": {
             "staging": [{"image": "led1.png", "delay": 500}, {"image": "led2.png", "delay": 0}]
         },
        "LED_COUNT": 64,

Images are 8x8 = 64
'''
from led_handler import Color
import gevent
import cv2

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
                    self.setPixels(img)
                    self.strip.show()
                    gevent.sleep(delay/1000.0)
        return render

    def setPixels(self, img):
        pos = 0
        for i in range(0, img.shape[0]):
            for j in range(0, img.shape[1]):
                if pos == self.strip.numPixels():
                    return
                self.strip.setPixelColor(pos, Color(img[i][j][2], img[i][j][1], img[i][j][0]))
                pos = pos + 1

def get_led_handler(strip, config, *args, **kwargs):
    return BitmapLEDHandler(strip, config['BITMAPS'])
