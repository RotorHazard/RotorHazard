'''LED visual effects'''

# to use this handler, run:
#    sudo apt-get install libjpeg-dev
#    sudo pip install pillow

import Config
from led_event_manager import LEDEffect, Color, ColorVal
import gevent
from PIL import Image, ImageDraw

def rssiGraph(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    if 'INTERFACE' in args:
        INTERFACE = args['INTERFACE']
    else:
        return False

    if len(INTERFACE.nodes) < 1:
        return False

    panel = getPanelImg(strip)

    if panel['width'] < len(INTERFACE.nodes):
        barWidth = 1
    else:
        barWidth = panel['width'] // len(INTERFACE.nodes)

    while True:
        panel['draw'].rectangle((0, 0, panel['width'], panel['height']), fill=(0, 0, 0))

        for node in INTERFACE.nodes:
            rssi_min = node.node_nadir_rssi
            rssi_max = node.node_peak_rssi
            rssi_val = node.current_rssi

            color = convertColor(args['manager'].getDisplayColor(node.index))

            rssi_range = rssi_max - rssi_min

            if rssi_range:
                point = (rssi_max - rssi_val) / float(rssi_range) * panel['height']

                panel['draw'].rectangle((barWidth * node.index, point, (barWidth * node.index) + barWidth - 1, panel['height']), fill=color)

        img = panel['im'].rotate(90 * Config.LED['PANEL_ROTATE'])
        setPixels(strip, img)
        strip.show()

        gevent.idle()

def getPanelImg(strip):
    width = int(strip.numPixels() / Config.LED['LED_ROWS'])
    height = Config.LED['LED_ROWS']
    im = Image.new('RGB', [width, height])
    return {
        'width': width,
        'height': height,
        'im': im,
        'draw': ImageDraw.Draw(im)
    }

def setPixels(strip, img):
    pos = 0
    for row in range(0, img.height):
        for col in range(0, img.width):
            if pos >= strip.numPixels():
                return

            c = col
            if Config.LED['INVERTED_PANEL_ROWS']:
                if row % 2 == 0:
                    c = 15 - col

            px = img.getpixel((c, row))
            strip.setPixelColor(pos, Color(px[0], px[1], px[2]))
            pos += 1

def clearPixels(strip):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, ColorVal.NONE)

def convertColor(color):
    return color >> 16, (color >> 8) % 256, color % 256

def discover(*args, **kwargs):
    effects = [
    LEDEffect(
        "graphRSSI",
        "Graph: RSSI",
        rssiGraph, {
            'include': [],
            'exclude': [],
            'recommended': []
        }, {}
        )
    ]

    return effects
