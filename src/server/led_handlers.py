'''LED visual effects'''

import gevent
import cv2
import numpy as np

def Color(red, green, blue):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return (red << 16) | (green << 8) | blue

class ColorVal:
    NONE = Color(0,0,0)
    BLUE = Color(0,31,255)
    CYAN = Color(0,255,255)
    DARK_ORANGE = Color(255,63,0)
    DARK_YELLOW = Color(250,210,0)
    GREEN = Color(0,255,0)
    LIGHT_GREEN = Color(127,255,0)
    ORANGE = Color(255,128,0)
    MINT = Color(63,255,63)
    PINK = Color(255,0,127)
    PURPLE = Color(127,0,255)
    RED = Color(255,0,0)
    SKY = Color(0,191,255)
    WHITE = Color(255,255,255)
    YELLOW = Color(255,255,0)

class ColorPattern:
    SOLID = 0
    ALTERNATING = 1
    TWO_OUT_OF_THREE = 2
    MOD_SEVEN = 3
    CUSTOM_RB_CYCLE = 4  # handled by subclass
    CHASE = 5  # handled by subclass
    RAINBOW = 6  # handled by subclass
    RAINBOW_CHASE = 7  # handled by subclass

nodeToColorArray = [ColorVal.BLUE, ColorVal.DARK_ORANGE, ColorVal.LIGHT_GREEN, ColorVal.YELLOW, \
                        ColorVal.PURPLE, ColorVal.PINK, ColorVal.MINT, ColorVal.SKY]

def led_on(strip, color, pattern=ColorPattern.SOLID):
    if pattern == ColorPattern.SOLID:
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
    elif pattern == ColorPattern.ALTERNATING:
        onFlag = True
        for i in range(strip.numPixels()):
            if onFlag:
                strip.setPixelColor(i, color)
                onFlag = False
            else:
                strip.setPixelColor(i, ColorVal.NONE)
                onFlag = True
    elif pattern == ColorPattern.TWO_OUT_OF_THREE:
        for i in range(strip.numPixels()):
            if (i + 1) % 3 != 0:
                strip.setPixelColor(i, color)
            else:
                strip.setPixelColor(i, ColorVal.NONE)
    elif pattern == ColorPattern.MOD_SEVEN:
        for i in range(strip.numPixels()):
            if i % 7 == 0:
                strip.setPixelColor(i, color)
            else:
                strip.setPixelColor(i, ColorVal.NONE)
    strip.show()

def led_off(strip):
    led_on(strip, ColorVal.NONE)

def led_theaterChase(strip, color, wait_ms=50, iterations=5):
    """Movie theater light style chaser animation."""
    led_on(strip, ColorVal.NONE)
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels()-q, 3):
                strip.setPixelColor(i+q, color)
            strip.show()
            gevent.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels()-q, 3):
                strip.setPixelColor(i+q, 0)

def color_wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def led_rainbow(strip, wait_ms=2, iterations=1):
    """Draw rainbow that fades across all pixels at once."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color_wheel((i) & 255))
    strip.show()
    gevent.sleep(wait_ms/1000.0)

def led_rainbowCycle(strip, wait_ms=2, iterations=1):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color_wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        gevent.sleep(wait_ms/1000.0)

def led_theaterChaseRainbow(strip, wait_ms=25):
    """Rainbow movie theater light style chaser animation."""
    led_on(strip, ColorVal.NONE)
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels()-q, 3):
                strip.setPixelColor(i+q, color_wheel((i+j) % 255))
            strip.show()
            gevent.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels()-q, 3):
                strip.setPixelColor(i+q, 0)

def showColor(strip, config, args):
    led_on(strip, args['color'])

def showBitmap(strip, config, args):
    def setPixels(img):
        pos = 0
        for row in range(0, img.shape[0]):
            for col in range(0, img.shape[1]):
                if pos == strip.numPixels():
                    return

                c = col
                if config['INVERTED_PANEL_ROWS']:
                    if row % 2 == 0:
                        c = 15 - col

                strip.setPixelColor(pos, Color(img[row][c][2], img[row][c][1], img[row][c][0]))
                pos += 1

    bitmaps = args['bitmaps']
    if bitmaps and bitmaps is not None:
        for bitmap in bitmaps:
            img = cv2.imread(bitmap['image']) # BGR
            delay = bitmap['delay']

            rotated = np.rot90(img, config['PANEL_ROTATE'])

            setPixels(rotated)
            strip.show()
            gevent.sleep(delay/1000.0)

def clear(strip, config, args=None):
    led_off(strip)

def hold(strip, config, args=None):
    pass

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

    # register generic color change
    handler.registerEventHandler("color", showColor, ["startup", "raceStaging", "raceRunning", "raceFinished", "raceStopped", "manual", "shutdown"], {'color': ColorVal.NONE})

    # register clear for all events
    handler.registerEventHandler("clear", clear, ["startup", "raceStaging", "crossingEntered", "crossingExisted","raceRunning", "raceFinished", "raceStopped", "manual", "shutdown"])

    # register hold/none for all events
    handler.registerEventHandler("none", hold, ["startup", "raceStaging", "crossingEntered", "crossingExisted", "raceRunning", "raceFinished", "raceStopped", "manual", "shutdown"])
