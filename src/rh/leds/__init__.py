import  gevent
from rh.util import ms_counter, millis_to_secs


def Color(red, green, blue):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return (red << 16) | (green << 8) | blue


def hexToColor(hexColor):
    return int(hexColor.replace('#', ''), 16)


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


def setPixels(strip, img, invertRows=False):
    pos = 0
    for row in range(0, img.height):
        for col in range(0, img.width):
            if pos >= strip.numPixels():
                return

            c = col
            if invertRows:
                if row % 2 == 0:
                    c = 15 - col

            px = img.getpixel((c, row))
            strip.setPixelColor(pos, Color(px[0], px[1], px[2]))
            pos += 1


def stagingEffects(start_time_ms, callback):
    if start_time_ms is not None:
        while ms_counter() < start_time_ms:
            diff_ms = start_time_ms - ms_counter()
            if diff_ms:
                diff_to_s = millis_to_secs(diff_ms % 1000)
                gevent.sleep(diff_to_s)
                callback(diff_ms)
            else:
                break
