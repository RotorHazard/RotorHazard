'''Dummy LED layer.'''

from colorama import init, Fore, Cursor
import logging
logger = logging.getLogger(__name__)

class ANSIPixel:
    def __init__(self, count, rows=1):
        '''Constructor'''
        self.pixels = [0 for _i in range(count)]
        if rows < 1:
            self.width = count
            self.height = 1
        else:
            self.width = count//rows
            self.height = rows

    def begin(self):
        init(autoreset=True)

    def numPixels(self):
        return len(self.pixels)

    def setPixelColor(self, i, color):
        self.pixels[i] = color

    def getPixelColor(self, i):
        return self.pixels[i]

    def show(self):
        start = 0
        row = 1
        while start < len(self.pixels):
            end = start + self.width
            print(Cursor.POS(1, row) + ''.join(self.getANSIPx(px) for px in self.pixels[start:end]))
            start = end
            row += 1

    def setBrightness(self, *args, **kwargs):
        pass

    def getANSIPx(self, color):
        r = color >> 16 & 0xff
        g = color >> 8  & 0xff
        b = color & 0xff

        if r < 32 and g < 32 and b < 32:
            c = Fore.BLACK
        elif r > 191 and g >= 191 and b >= 191:
            c = Fore.WHITE
        elif r > 191 and g < 64 and b < 64:
            c = Fore.LIGHTRED_EX
        elif r < 64 and g > 191 and b < 64:
            c = Fore.LIGHTGREEN_EX
        elif r < 64 and g < 64 and b > 191:
            c = Fore.LIGHTBLUE_EX
        elif r > 127 and g > 127 and b < 128:
            c = Fore.LIGHTYELLOW_EX
        elif r > 127 and g < 128 and b > 127:
            c = Fore.LIGHTMAGENTA_EX
        elif r < 128 and g > 127 and b > 127:
            c = Fore.LIGHTCYAN_EX
        elif r > 31 and g < 32 and b < 32:
            c = Fore.RED
        elif r < 32 and g > 31 and b < 32:
            c = Fore.GREEN
        elif r < 32 and g < 32 and b > 31:
            c = Fore.BLUE
        elif r > 31 and g > 31 and b < 32:
            c = Fore.YELLOW
        elif r > 31 and g < 32 and b > 31:
            c = Fore.MAGENTA
        elif r < 32 and g > 31 and b > 31:
            c = Fore.CYAN
        elif r > 127 and g > 127 and b > 127:
            c = Fore.WHITE
        else:
            c = Fore.BLACK

        return c+'*'

def get_pixel_interface(config, brightness, *args, **kwargs):
    '''Returns the pixel interface.'''
    logger.info('LED: locally emulated via ANSIPixel')
    return ANSIPixel(config['LED_COUNT'], config.get('LED_ROWS', 1))
