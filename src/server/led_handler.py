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
    def __init__(self, strip):
        self.strip = strip

    def isEnabled(self):
        return False

    def startup(self):
        pass
        
    def shutdown(self):
        pass

    def raceStaging(self):
        pass

    def raceStarted(self):
        pass

    def raceStopped(self):
        pass

    def raceFinished(self):
        pass

    def clear(self):
        pass

    def crossingEntered(self, node):
        pass

    def crossingExited(self, node):
        pass
