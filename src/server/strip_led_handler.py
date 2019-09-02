'''Standard LED strip handler.'''
from led_handler import LEDHandler, Color, led_on, led_off
import time

def led_theaterChase(strip, color, wait_ms=50, iterations=5):
    """Movie theater light style chaser animation."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, color)
            strip.show()
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
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
        time.sleep(wait_ms/1000.0)

def led_rainbowCycle(strip, wait_ms=2, iterations=1):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color_wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms/1000.0)

def led_theaterChaseRainbow(strip, wait_ms=25):
    """Rainbow movie theater light style chaser animation."""
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, color_wheel((i+j) % 255))
            strip.show()
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

class StripLEDHandler(LEDHandler):
    def __init__(self, strip):
        LEDHandler.__init__(self, strip)

    def staging(self):
        led_on(self.strip, COLOR_ORANGE)

    def start(self):
        led_on(self.strip, COLOR_GREEN)

    def pass_record(self, node):
        if node.index==0:
            led_on(self.strip, COLOR_BLUE)
        elif node.index==1:
            led_on(self.strip, COLOR_DARK_ORANGE)
        elif node.index==2:
            led_on(self.strip, COLOR_PINK)
        elif node.index==3:
            led_on(self.strip, COLOR_PURPLE)
        elif node.index==4:
            led_on(self.strip, COLOR_YELLOW)
        elif node.index==5:
            led_on(self.strip, COLOR_CYAN)
        elif node.index==6:
            led_on(self.strip, COLOR_GREEN)
        elif node.index==7:
            led_on(self.strip, COLOR_RED)

    def stop(self):
        led_on(self.strip, COLOR_RED)

def get_led_handler(strip, config, *args, **kwargs):
    return StripLEDHandler(strip)
