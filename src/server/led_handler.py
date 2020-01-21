'''Generic LED handler stuff.'''

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
    RAINBOW = 6
    RAINBOW_CHASE = 7

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

class LEDHandler:
    onRacePrepareFlag = False
    RACE_PREPARE_COLOR = ColorVal.DARK_ORANGE
    VTX_COLOR_LINGER_TIME = 5  # delay before clearing colors via VTX enter/pass (seconds)
    RACE_COLOR_LINGER_TIME = 300  # delay before clearing race stage/start/stop colors (seconds)

    nodeToColorArray = [ColorVal.BLUE, ColorVal.DARK_ORANGE, ColorVal.LIGHT_GREEN, ColorVal.YELLOW, \
                        ColorVal.PURPLE, ColorVal.PINK, ColorVal.MINT, ColorVal.SKY]

    def __init__(self, strip, config):
        self.strip = strip
        self.config = config
        self.strip_handler = StripLEDHandler(strip)
        self.bitmap_handler = BitmapLEDHandler(strip, config['BITMAPS'])

    def isEnabled(self):
        return True

    def event(self, event, **kwargs):
        if event is "startup":
            if self.config["HANDLER"] == "bitmap":
                self.bitmap_handler.displayImage(self.config["BITMAPS"]['startup'])
            else:
                self.strip_handler.cmdStripColor(ColorVal.BLUE, ColorPattern.CUSTOM_RB_CYCLE, 1)

        elif event is "shutdown":
            self.strip_handler.processCurrentColor = ColorVal.NONE
            led_off(self.strip)

        elif event is "racePrepare":
            self.strip_handler.cmdStripColor(self.RACE_PREPARE_COLOR, ColorPattern.MOD_SEVEN, self.RACE_COLOR_LINGER_TIME)
            self.onRacePrepareFlag = True

        elif event is "raceStaging":
            if self.config["HANDLER"] == "bitmap":
                self.bitmap_handler.displayImage(self.config["BITMAPS"]['raceStaging'])
            else:
                self.strip_handler.cmdStripColor(ColorVal.ORANGE, ColorPattern.TWO_OUT_OF_THREE, self.RACE_COLOR_LINGER_TIME)

        elif event is "raceStarted":
            if self.config["HANDLER"] == "bitmap":
                self.bitmap_handler.displayImage(self.config["BITMAPS"]['raceStarted'])
            else:
                self.strip_handler.cmdStripColor(ColorVal.GREEN, ColorPattern.SOLID, self.VTX_COLOR_LINGER_TIME*2)  # race is running so clear after a short time

        elif event is "raceStopped":
            if self.config["HANDLER"] == "bitmap":
                self.bitmap_handler.displayImage(self.config["BITMAPS"]['raceStopped'])
            else:
                self.strip_handler.cmdStripColor(ColorVal.RED, ColorPattern.SOLID, self.RACE_COLOR_LINGER_TIME)

        elif event is "raceFinished":
            if self.config["HANDLER"] == "bitmap":
                self.bitmap_handler.displayImage(self.config["BITMAPS"]['raceFinished'])

        elif event is "crossingEntered":
            if 'node' in kwargs:
                node = kwargs['node']
                self.strip_handler.cmdStripColor(self.nodeToColorArray[node.index%len(self.nodeToColorArray)], \
                               ColorPattern.SOLID)  # crossings should be short term, so stay on until next event

        elif event is "crossingExited":
            if 'node' in kwargs:
                node = kwargs['node']
                self.strip_handler.cmdStripColor(self.nodeToColorArray[node.index%len(self.nodeToColorArray)], \
                           ColorPattern.ALTERNATING, self.VTX_COLOR_LINGER_TIME)

        elif event is "manualChange":
            color = kwargs['color']
            pattern = kwargs['pattern']
            time = kwargs['time']
            self.strip_handler.cmdStripColor(color, pattern, time)
            pass

    def clear(self):
        self.strip_handler.cmdStripColor(ColorVal.NONE, ColorPattern.SOLID)

    def idle(self):
        pass

    # return True if last call was to 'racePrepare()' fn (and hasn't timed out)
    def isOnRacePrepare(self):
        if self.onRacePrepareFlag:
            if self.config['HANDLER'] is 'strip':
                return self.strip_handler.processCurrentColor == self.RACE_PREPARE_COLOR
        return False

class NoLEDHandler(LEDHandler):
    def __init__(self):
        LEDHandler.__init__(self, None)

    def isEnabled(self):
        return False

    def event(*args, **kwargs):
        pass

    def clear(*args, **kwargs):
        pass

    def isOnRacePrepare(*args, **kwargs):
        return False



import gevent
from monotonic import monotonic

def led_theaterChase(strip, color, wait_ms=50, iterations=5):
    """Movie theater light style chaser animation."""
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
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color_wheel((i+j) & 255))
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
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels()-q, 3):
                strip.setPixelColor(i+q, color_wheel((i+j) % 255))
            strip.show()
            gevent.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels()-q, 3):
                strip.setPixelColor(i+q, 0)

class StripLEDHandler:
    processEventObj = gevent.event.Event()
    processCurrentColor = ColorVal.NONE
    processCurrentPattern = ColorPattern.SOLID
    processLastSetColorTime = monotonic()
    processColorLingerTime = 0

    def __init__(self, strip):
        self.strip = strip
        gevent.spawn(self.processThreadFn)

    def processThreadFn(self):
        gevent.sleep(0.250)  # start with a sleep to let other startup threads run
        while True:
            if self.processEventObj.wait(0.250):  # wait for timeout or event flag set
                self.processEventObj.clear()
                self.processLastSetColorTime = monotonic()
                if self.processCurrentPattern is ColorPattern.CUSTOM_RB_CYCLE:
                    led_rainbowCycle(self.strip)
                elif self.processCurrentPattern is ColorPattern.CHASE:
                    led_theaterChase(self.strip, self.processCurrentColor)
                elif self.processCurrentPattern is ColorPattern.RAINBOW:
                    led_rainbow(self.strip)
                elif self.processCurrentPattern is ColorPattern.RAINBOW_CHASE:
                    led_theaterChaseRainbow(self.strip)
                else:
                    led_on(self.strip, self.processCurrentColor, self.processCurrentPattern)
            elif self.processCurrentColor != ColorVal.NONE and self.processColorLingerTime > 0 and \
                        monotonic() > self.processLastSetColorTime + self.processColorLingerTime:
                self.processCurrentColor = ColorVal.NONE
                led_off(self.strip)

    def cmdStripColor(self, clrVal, clrPat, lingerTime=0):
        self.processCurrentColor = clrVal
        self.processCurrentPattern = clrPat
        self.processColorLingerTime = lingerTime
        self.processEventObj.set()  # interrupt event 'wait' in 'processThreadFn()'
        self.onRacePrepareFlag = False



'''
Renders bitmaps to LEDs.
Example config:
    "LED": {
        "HANDLER": "bitmap",
        "BITMAPS": {
            "raceStaging": [{"image": "led-staging.png", "delay": 0}],
            "raceStarted": [{"image": "led-start-1.png", "delay": 500}, {"image": "led-start-2.png", "delay": 0}],
            "PANEL_ROTATE": 0,
            "INVERTED_PANEL_ROWS": false
        }

Bitmap dimensions must match LED panel dimensions for accurate display.

'''
import cv2
import numpy as np

class BitmapLEDHandler:
    def __init__(self, strip, config):
        self.strip = strip
        self.config = config

    def displayImage(self, name):
        bitmaps = name
        if bitmaps is not None:
            for bitmap in bitmaps:
                img = cv2.imread(bitmap['image']) # BGR
                delay = bitmap['delay']

                rotated = np.rot90(img, self.config['PANEL_ROTATE'])

                self.setPixels(rotated)
                self.strip.show()
                gevent.sleep(delay/1000.0)

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
