'''Generic LED handler stuff.'''

def Color(red, green, blue):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return (red << 16) | (green << 8) | blue

COLOR_NONE = Color(0,0,0)
COLOR_BLUE = Color(0,0,255)
COLOR_CYAN = Color(0,255,255)
COLOR_DARK_ORANGE = Color(255,50,0)
COLOR_GREEN = Color(0,255,0)
COLOR_ORANGE = Color(255,128,0)
COLOR_PINK = Color(255,0,60)
COLOR_PURPLE = Color(150,0,255)
COLOR_RED = Color(255,0,0)
COLOR_YELLOW = Color(250,210,0)

def led_on(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

def led_off(strip):
    led_on(strip, COLOR_NONE)

class LEDHandler:
    def __init__(self, strip):
        self.strip = strip

    def staging(self):
        pass

    def start(self):
        pass

    def pass_record(self, node):
        pass

    def stop(self):
        pass
