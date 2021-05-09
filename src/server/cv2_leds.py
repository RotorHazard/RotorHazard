'''LED emulation via CV2 image'''

# to use this emulator, run:
#    sudo pip install opencv-python

import numpy as np  #pylint: disable=import-error
import cv2  #pylint: disable=import-error
import logging
logger = logging.getLogger(__name__)

class cv2_LED_emulation:
    scale = 16

    def __init__(self, count, rows=1):
        '''Constructor'''
        self.pixels = [0 for _i in range(count)]
        self.width = count//rows
        self.height = rows

    def begin(self):
        pass

    def numPixels(self):
        return len(self.pixels)

    def setPixelColor(self, i, color):
        self.pixels[i] = color

    def getPixelColor(self, i):
        return self.pixels[i]

    def show(self):
        image = np.zeros((self.height, self.width, 3), np.uint8)

        for i in range(len(self.pixels)):
            c = i % self.width
            r = i // self.width
            image[r, c] = tuple(reversed(convertColor(self.pixels[i])))

        image = cv2.resize(image, (self.width*self.scale, self.height*self.scale), interpolation=cv2.INTER_NEAREST)

        cv2.imshow('RotorHazard LED Preview', image)
        cv2.waitKey(1)

    def setBrightness(self, *args, **kwargs):
        pass

def convertColor(color):
    return [color >> 16, (color >> 8) % 256, color % 256]

def get_pixel_interface(config, brightness, *args, **kwargs):
    '''Returns the pixel interface.'''
    logger.info('LED: locally emulated via OpenCV')
    return cv2_LED_emulation(config['LED_COUNT'], config.get('LED_ROWS', 1))
