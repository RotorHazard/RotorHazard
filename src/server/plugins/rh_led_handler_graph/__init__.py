'''LED visual effects'''

# to use this handler, run:
#    sudo apt-get install libjpeg-dev
#    sudo pip install pillow

import Config
from led_event_manager import LEDEffect, Color, ColorVal
import gevent
from PIL import Image, ImageDraw

def registerHandlers(args):
    if 'registerFn' in args:
        for led_effect in discover():
            args['registerFn'](led_effect)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('LED_Initialize', 'LED_register_graph', registerHandlers, {}, 75)

def rssiGraph(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    if 'raceContext' in args:
        INTERFACE = args['raceContext'].interface
    else:
        return False

    if len(INTERFACE.nodes) < 1:
        return False

    panel = getPanelImg(strip)

    if 'active_only' in args and args['active_only'] == True:
        active_nodes = []
        for node in INTERFACE.nodes:
            if node.frequency:
                active_nodes.append(node)

    else:
        active_nodes = INTERFACE.nodes

    if panel['width'] < len(active_nodes):
        barWidth = 1
    else:
        barWidth = panel['width'] // len(active_nodes)

    while True:
        panel['draw'].rectangle((0, 0, panel['width'], panel['height']), fill=(0, 0, 0))

        for node in active_nodes:
            rssi_min = node.node_nadir_rssi
            rssi_max = node.node_peak_rssi
            rssi_val = node.current_rssi

            color = convertColor(args['manager'].getDisplayColor(node.index))

            rssi_range = rssi_max - rssi_min

            if rssi_range:
                point = (rssi_max - rssi_val) / float(rssi_range) * panel['height']

                panel['draw'].rectangle((barWidth * node.index, point, (barWidth * node.index) + barWidth - 1, panel['height']), fill=color)

        img = panel['im'].rotate(90 * Config.LED['PANEL_ROTATE'], expand=True)
        setPixels(strip, img)
        strip.show()

        gevent.idle()

def getPanelImg(strip):
    panel_w = Config.LED['LED_COUNT'] // Config.LED['LED_ROWS']
    panel_h = Config.LED['LED_ROWS']

    if Config.LED['PANEL_ROTATE'] % 2:
        width = panel_h
        height = panel_w
    else:
        width = panel_w
        height = panel_h

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
        "Graph: RSSI (all)",
        rssiGraph, {
            'include': [],
            'exclude': [],
            'recommended': []
        }, {}
        ),
    LEDEffect(
        "graphRSSIActive",
        "Graph: RSSI (enabled)",
        rssiGraph, {
            'include': [],
            'exclude': [],
            'recommended': []
        }, {
            'active_only': True
        }
        )
    ]

    return effects
