'''Generic LED handler stuff.'''

def Color(red, green, blue):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return (red << 16) | (green << 8) | blue

class ColorVal:
    NONE = Color(0,0,0)
    BLUE = Color(0,0,255)
    CYAN = Color(0,255,255)
    DARK_ORANGE = Color(255,50,0)
    GREEN = Color(0,255,0)
    ORANGE = Color(255,128,0)
    PINK = Color(255,0,60)
    PURPLE = Color(150,0,255)
    RED = Color(255,0,0)
    YELLOW = Color(250,210,0)

class ColorPattern:
    SOLID = 0
    ALTERNATING = 1
    TWO_OUT_OF_THREE = 2
    CUSTOM_RB_CYCLE = 3  # handled by subclass

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
    strip.show()

def led_off(strip):
    led_on(strip, ColorVal.NONE)

class LEDHandler:
    def __init__(self, strip):
        self.strip = strip

    def startup(self):
        pass

    def staging(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def pass_record(self, node):
        pass

    def crossing_entered(self, node):
        pass
        
    def showRainbowCycle(self):
        pass

    def finished(self):
        pass
