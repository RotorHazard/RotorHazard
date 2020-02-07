'''Dummy LED layer.'''

from colorama import init, Fore, Cursor

class ANSIPixel:
    def __init__(self, count, rows=1):
        '''Constructor'''
        self.pixels = [0 for i in range(count)]
        self.width = count/rows

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
            print Cursor.POS(1, row) + ''.join(self.getANSIPx(px) for px in self.pixels[start:end])
            start = end
            row += 1

    def setBrightness(*args, **kwargs):
        pass

    def getANSIPx(self, color):
        r = color >> 16 & 0xff
        g = color >> 8  & 0xff
        b = color & 0xff
        if color == 0:
            c = Fore.BLACK
        elif r == 255 and g == 255 and b == 255:
            c = Fore.WHITE
        elif r == 255 and g == 0 and b == 0:
            c = Fore.LIGHTRED_EX
        elif r == 0 and g == 255 and b == 0:
            c = Fore.LIGHTGREEN_EX
        elif r == 0 and g == 0 and b == 255:
            c = Fore.LIGHTBLUE_EX
        elif r > 128 and g > 128 and b < 128:
            c = Fore.LIGHTYELLOW_EX
        elif r > 128 and g < 128 and b > 128:
            c = Fore.LIGHTMAGENTA_EX
        elif r < 128 and g > 128 and b > 128:
            c = Fore.LIGHTCYAN_EX
        elif r > 0 and g == 0 and b == 0:
            c = Fore.RED
        elif r == 0 and g > 0 and b == 0:
            c = Fore.GREEN
        elif r == 0 and g == 0 and b > 0:
            c = Fore.BLUE
        elif r > 0 and g > 0 and b == 0:
            c = Fore.YELLOW
        elif r > 0 and g == 0 and b > 0:
            c = Fore.MAGENTA
        elif r == 0 and g > 0 and b > 0:
            c = Fore.CYAN
        else:
            c = Fore.BLACK

        return c+'*'

def get_pixel_interface(config, brightness, *args, **kwargs):
    '''Returns the pixel interface.'''
    print('LED: locally enabled via ANSIPixel')
    return ANSIPixel(config['LED_COUNT'], config.get('LED_ROWS', 1))
