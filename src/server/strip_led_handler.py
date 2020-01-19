'''Standard LED strip handler.'''
from led_handler import LEDHandler, Color, ColorVal, ColorPattern, led_on, led_off
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

class StripLEDHandler(LEDHandler):
    
    processEventObj = gevent.event.Event()
    processCurrentColor = ColorVal.NONE
    processCurrentPattern = ColorPattern.SOLID
    processLastSetColorTime = monotonic()
    processColorLingerTime = 0
    VTX_COLOR_LINGER_TIME = 5  # delay before clearing colors via VTX enter/pass (seconds)
    RACE_COLOR_LINGER_TIME = 300  # delay before clearing race stage/start/stop colors (seconds)
    
    nodeToColorArray = [ColorVal.BLUE, ColorVal.DARK_ORANGE, ColorVal.LIGHT_GREEN, ColorVal.YELLOW, \
                        ColorVal.PURPLE, ColorVal.PINK, ColorVal.MINT, ColorVal.SKY]
    
    def __init__(self, strip):
        LEDHandler.__init__(self, strip)
        gevent.spawn(self.processThreadFn)
    
    def processThreadFn(self):
        gevent.sleep(0.250)  # start with a sleep to let other startup threads run
        while True:
            if self.processEventObj.wait(0.250):  # wait for timeout or event flag set
                self.processEventObj.clear()
                self.processLastSetColorTime = monotonic()
                if self.processCurrentPattern != ColorPattern.CUSTOM_RB_CYCLE:
                    led_on(self.strip, self.processCurrentColor, self.processCurrentPattern)
                else:
                    led_rainbowCycle(self.strip)
            elif self.processCurrentColor != ColorVal.NONE and self.processColorLingerTime > 0 and \
                        monotonic() > self.processLastSetColorTime + self.processColorLingerTime:
                self.processCurrentColor = ColorVal.NONE
                led_off(self.strip)
        
    def cmdStripColor(self, clrVal, clrPat, lingerTime=0):
        self.processCurrentColor = clrVal
        self.processCurrentPattern = clrPat
        self.processColorLingerTime = lingerTime
        self.processEventObj.set()  # interrupt event 'wait' in 'processThreadFn()'
        
    def staging(self):
        self.cmdStripColor(ColorVal.ORANGE, ColorPattern.TWO_OUT_OF_THREE, self.RACE_COLOR_LINGER_TIME)

    def start(self):
        self.cmdStripColor(ColorVal.GREEN, ColorPattern.SOLID, self.VTX_COLOR_LINGER_TIME)  # race is running so clear after a short time

    def stop(self):
        self.cmdStripColor(ColorVal.RED, ColorPattern.SOLID, self.RACE_COLOR_LINGER_TIME)

    def pass_record(self, node):
        self.cmdStripColor(self.nodeToColorArray[node.index%len(self.nodeToColorArray)], \
                           ColorPattern.ALTERNATING, self.VTX_COLOR_LINGER_TIME)

    def crossing_entered(self, node):
        self.cmdStripColor(self.nodeToColorArray[node.index%len(self.nodeToColorArray)], \
                           ColorPattern.SOLID)  # crossings should be short term, so stay on until next event
        
    def startup(self):
        self.cmdStripColor(ColorVal.BLUE, ColorPattern.CUSTOM_RB_CYCLE, 1)
        
    def shutdown(self):
        led_off(self.strip)

def get_led_handler(strip, config, *args, **kwargs):
    return StripLEDHandler(strip)
