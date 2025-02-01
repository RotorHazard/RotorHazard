'''LED visual effects'''

# To use this LED-panel plugin see:
#   https://github.com/RotorHazard/RotorHazard/blob/main/doc/Software%20Setup.md#led-panel-support

import logging
from eventmanager import Evt
from led_event_manager import LEDEffect, LEDEvent, Color, ColorVal, effect_delay

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw
except ModuleNotFoundError as ex:
    logger.debug(str(ex) + " ('pillow' module needed to use '" + __name__ + "')")
    raise ModuleNotFoundError("'pillow' module not found") from ex

def rssiGraph(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    if 'RHAPI' in args:
        INTERFACE = args['RHAPI'].interface
    else:
        return False

    if len(INTERFACE.seats) < 1:
        return False

    panel = getPanelImg(strip, args)

    if args.get('active_only'):
        active_nodes = []
        for node in INTERFACE.seats:
            if node.frequency:
                active_nodes.append(node)

    else:
        active_nodes = INTERFACE.seats

    logger.debug(active_nodes)

    if panel['width'] < len(active_nodes):
        barWidth = 1
    else:
        barWidth = panel['width'] // len(active_nodes)

    while True:
        panel['draw'].rectangle((0, 0, panel['width'], panel['height']), fill=(0, 0, 0))

        for idx, node in enumerate(active_nodes):
            rssi_min = node.node_nadir_rssi
            rssi_max = node.node_peak_rssi
            rssi_val = node.current_rssi

            color = convertColor(args['manager'].getDisplayColor(node.index))

            rssi_range = rssi_max - rssi_min

            if rssi_range:
                point = (rssi_max - rssi_val) / float(rssi_range) * panel['height']

                panel['draw'].rectangle((barWidth * idx, point, (barWidth * idx) + barWidth - 1, panel['height']), fill=color)

        img = panel['im'].rotate(90 * args['RHAPI'].config.get('LED', 'PANEL_ROTATE'), expand=True)
        setPixels(strip, img, args)
        strip.show()

        effect_delay(100, args)

def getPanelImg(strip, args):
    panel_w = args['RHAPI'].config.get('LED', 'LED_COUNT', as_int=True) // args['RHAPI'].config.get('LED', 'LED_ROWS', as_int=True)
    panel_h = args['RHAPI'].config.get('LED', 'LED_ROWS', as_int=True)

    if args['RHAPI'].config.get('LED', 'PANEL_ROTATE', as_int=True) % 2:
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

def setPixels(strip, img, args):
    pos = 0
    for row in range(0, img.height):
        for col in range(0, img.width):
            if pos >= strip.numPixels():
                return

            c = col
            if args['RHAPI'].config.get('LED', 'INVERTED_PANEL_ROWS', as_int=True):
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

def register_handlers(args):
    for led_effect in [
        LEDEffect(
            "Graph: RSSI (all)",
            rssiGraph, {
                'include': [LEDEvent.IDLE_DONE, LEDEvent.IDLE_READY, LEDEvent.IDLE_RACING],
                'exclude': [],
                'recommended': []
            },
            {},
            name='graphRSSI',
        ),
        LEDEffect(
            "Graph: RSSI (enabled)",
            rssiGraph, {
                'include': [LEDEvent.IDLE_DONE, LEDEvent.IDLE_READY, LEDEvent.IDLE_RACING],
                'exclude': [],
                'recommended': []
            }, {
                'active_only': True
            },
            name='graphRSSIActive',
        )
    ]:
        args['register_fn'](led_effect)

def initialize(rhapi):
    rhapi.events.on(Evt.LED_INITIALIZE, register_handlers)

