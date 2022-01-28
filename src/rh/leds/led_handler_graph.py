'''LED visual effects'''

# to use this handler, run:
#    sudo apt-get install libjpeg-dev
#    sudo pip install pillow

from . import ColorVal, setPixels
from rh.events.led_event_manager import LEDEffect
import gevent
from PIL import Image, ImageDraw
from itertools import repeat

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

    height = args['ledRows']
    width = strip.numPixels() // height
    im = Image.new('RGB', [width, height])
    draw = ImageDraw.Draw(im)

    if width < len(INTERFACE.nodes):
        barWidth = 1
    else:
        barWidth = width // len(INTERFACE.nodes)

    loop = range(args['iterations']) if 'iterations' in args else repeat(True)
    for _ in loop:
        draw.rectangle((0, 0, width, height), fill=(0, 0, 0))

        for node in INTERFACE.nodes:
            rssi_min = node.node_nadir_rssi
            rssi_max = node.node_peak_rssi
            rssi_val = node.current_rssi.rssi

            color = convertColor(args['manager'].getDisplayColor(node.index))

            rssi_range = rssi_max - rssi_min

            if rssi_range:
                point = (rssi_max - rssi_val) / float(rssi_range) * height

                draw.rectangle((barWidth * node.index, point, (barWidth * node.index) + barWidth - 1, height), fill=color)

        img = im.rotate(90 * args['panelRotate'])
        setPixels(strip, img, args['invertedPanelRows'])
        strip.show()

        gevent.idle()

def clearPixels(strip):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, ColorVal.NONE)

def convertColor(color):
    return color >> 16, (color >> 8) % 256, color % 256

def discover(config, *args, **kwargs):
    effects = [
    LEDEffect(
        "graphRSSI",
        "Graph: RSSI",
        rssiGraph, {
            'include': [],
            'exclude': [],
            'recommended': []
        }, {
            'ledRows': config['LED_ROWS'],
            'panelRotate': config['PANEL_ROTATE'],
            'invertedPanelRows': config['INVERTED_PANEL_ROWS']
        }
        )
    ]

    return effects
