'''LED graphing of node RSSI values'''

# This plugin creates LED effects that display node RSSI values as bar graphs.
# See the 'register_handlers()' function below for effect names and parameters.
# LED strips and panels are supported (panels when LED row count is > 1).
# An LED strip can be laid out in a "serpentine" pattern to display multiple nodes on a single strip.
#
# For LED-panel configuration setup see:
#   https://github.com/RotorHazard/RotorHazard/blob/main/doc/Software%20Setup.md#led-panel-support

import logging
from eventmanager import Evt
from led_event_manager import LEDEffect, LEDEvent, Color, ColorVal, effect_delay

logger = logging.getLogger(__name__)

Pil_avail_flag = False
try:
    from PIL import Image, ImageDraw
    Pil_avail_flag = True
except ModuleNotFoundError as ex:
    logger.debug(str(ex) + " ('pillow' module not available for '" + __name__ + "')")

class NodeToLEDMapping:
    def __init__(self, led_first_idx, led_last_idx):
        self.led_first_idx = led_first_idx
        self.led_last_idx = led_last_idx
        self.idx_range = abs(led_last_idx - led_first_idx) + 1
        self.prev_disp_val = 0

def rssiGraph(args):
    if 'strip' not in args or 'RHAPI' not in args:
        return False
    strip = args['strip']

    rhapi = args['RHAPI']
    INTERFACE = rhapi.interface
    led_count = rhapi.config.get('LED', 'LED_COUNT', as_int=True)

    if len(INTERFACE.seats) < 1 or led_count < 1:
        return False

    if args.get('active_only'):
        active_nodes = []
        for node in INTERFACE.seats:
            if node.frequency:
                active_nodes.append(node)
    else:
        active_nodes = INTERFACE.seats
    if len(active_nodes) < 1:
        return False

    if args.get('single_node_only'):
        single_node_idx = args.get('single_node_idx', -1)
        if single_node_idx >= 0:
            for node in active_nodes:
                if node.index == single_node_idx:
                    active_nodes = [ node ]
                    break
            else:
                active_nodes = active_nodes[0:1]
                logger.warning("rh_led_handler_graph Unable to match 'single_node_idx' value ({}); using node: {}".\
                               format(single_node_idx, active_nodes[0].index+1))
        else:
            active_nodes = active_nodes[0:1]

    logger.debug("rh_led_handler_graph active nodes: {}".format(active_nodes))

    if rhapi.config.get('LED', 'LED_ROWS', as_int=True) > 1:

        if not Pil_avail_flag:
            logger.error("Cannot display to LED panel because 'pillow' module not installed")
            return False

        panel = getPanelImg(strip, rhapi)

        if panel['width'] < len(active_nodes):
            barWidth = 1
        else:
            barWidth = panel['width'] // len(active_nodes)

        use_enter_exit_ats_flag = args.get('use_enter_exit_ats', False)

        while True:
            panel['draw'].rectangle((0, 0, panel['width'], panel['height']), fill=(0, 0, 0))

            for idx, node in enumerate(active_nodes):
                rssi_min = node.node_nadir_rssi if not use_enter_exit_ats_flag else node.exit_at_level
                rssi_max = node.node_peak_rssi if not use_enter_exit_ats_flag else node.enter_at_level
                rssi_val = max(rssi_min, min(node.current_rssi, rssi_max))  # bound value to min/max
                color = convertColor(args['manager'].getDisplayColor(node.index))
                rssi_range = rssi_max - rssi_min
                if rssi_range > 0:
                    point = (rssi_max - rssi_val) / float(rssi_range) * panel['height']
                    panel['draw'].rectangle((barWidth * idx, point, (barWidth * idx) + barWidth - 1, panel['height']), fill=color)

            img = panel['im'].rotate(90 * rhapi.config.get('LED', 'PANEL_ROTATE'), expand=True)
            setImgPixels(strip, img, rhapi)
            strip.show()
            effect_delay(100, args)

    else:
        node_mappings_dict = {}
        led_strip_pixels = [ColorVal.NONE] * led_count
        node_count = len(active_nodes)
        pixels_per_node_arr = [led_count // node_count] * node_count
        # if LED count is odd then add extra pixels to the total for each node as needed
        # (for example if LED count is 142 and four nodes, setup these counts: 36, 35, 36, 35)
        pix_total = pixels_per_node_arr[0] * node_count
        if pix_total < led_count:
            pixels_per_node_arr[0] += 1
            pix_total += 1
            if pix_total < led_count and node_count > 2:
                pixels_per_node_arr[2] += 1
                pix_total += 1
                if pix_total < led_count:
                    pixels_per_node_arr[1] += 1
        # setup mapping of first/last pixel index for each node
        serpentine_flag = args.get('serpentine', False)
        pix_total = 0
        for idx, node in enumerate(active_nodes):
            first_idx = pix_total
            pix_total += pixels_per_node_arr[idx]
            last_idx = pix_total - 1
            if (not serpentine_flag) or idx % 2 == 0:
                node_mappings_dict[node.index] = NodeToLEDMapping(first_idx, last_idx)
                logger.debug("rh_led_handler_graph node_idx={}, cnt={}, first={}, last={}".\
                             format(idx, pixels_per_node_arr[idx], first_idx, last_idx))
            else:  # if serpentine then alternate order on each node
                node_mappings_dict[node.index] = NodeToLEDMapping(last_idx, first_idx)
                logger.debug("rh_led_handler_graph node_idx={}, cnt={}, first={}, last={}". \
                             format(idx, pixels_per_node_arr[idx], last_idx, first_idx))
        use_enter_exit_ats_flag = args.get('use_enter_exit_ats', False)

        while True:
            for node in active_nodes:
                map_obj = node_mappings_dict.get(node.index)
                if map_obj:
                    rssi_min = node.node_nadir_rssi if not use_enter_exit_ats_flag else node.exit_at_level
                    rssi_max = node.node_peak_rssi if not use_enter_exit_ats_flag else node.enter_at_level
                    diff_val = rssi_max - rssi_min
                    if diff_val < 1:
                        diff_val = 1
                    disp_val = node.current_rssi - rssi_min
                    if disp_val < 0:
                        disp_val = 0
                    disp_val = disp_val / diff_val
                    if disp_val > 1.0:
                        disp_val = 1.0
                    manager_obj = args.get('manager')
                    node_clr = manager_obj.getDisplayColor(node.index) if manager_obj else ColorVal.YELLOW
                    updated_flag = False
                    if map_obj.led_first_idx <= map_obj.led_last_idx:
                        disp_val = round(disp_val * map_obj.idx_range)  # number of LEDs to set to color
                        if disp_val != map_obj.prev_disp_val:
                            if disp_val > 0:  # show colors (bar) followed by blanks
                                led_strip_pixels[map_obj.led_first_idx:map_obj.led_first_idx+disp_val] = \
                                                [node_clr] * disp_val
                            if disp_val < map_obj.idx_range:
                                led_strip_pixels[map_obj.led_first_idx+disp_val:map_obj.led_last_idx+1] = \
                                                [ColorVal.NONE] * (map_obj.idx_range - disp_val)
                            map_obj.prev_disp_val = disp_val
                            updated_flag = True
                    else:  # show colors in reverse order on strip
                        disp_val = map_obj.idx_range - round(disp_val * map_obj.idx_range)  # number of LEDs to set to none
                        if disp_val != map_obj.prev_disp_val:
                            if disp_val > 0:  # show blanks followed by colors (bar)
                                led_strip_pixels[map_obj.led_last_idx:map_obj.led_last_idx+disp_val] = \
                                                [ColorVal.NONE] * disp_val
                            if disp_val < map_obj.idx_range:
                                led_strip_pixels[map_obj.led_last_idx+disp_val:map_obj.led_first_idx+1] = \
                                                [node_clr] * (map_obj.idx_range - disp_val)
                            map_obj.prev_disp_val = disp_val
                            updated_flag = True
                    if updated_flag:
                        for i, clr in enumerate(led_strip_pixels):
                            strip.setPixelColor(i, clr)
                        strip.show()
            effect_delay(100, args)

def getPanelImg(strip, rhapi):
    panel_w = rhapi.config.get('LED', 'LED_COUNT', as_int=True) // rhapi.config.get('LED', 'LED_ROWS', as_int=True)
    panel_h = rhapi.config.get('LED', 'LED_ROWS', as_int=True)

    if rhapi.config.get('LED', 'PANEL_ROTATE', as_int=True) % 2:
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

def setImgPixels(strip, img, rhapi):
    pos = 0
    for row in range(0, img.height):
        for col in range(0, img.width):
            if pos >= strip.numPixels():
                return

            c = col
            if rhapi.config.get('LED', 'INVERTED_PANEL_ROWS', as_int=True):
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
    rhapi = args['RHAPI']
    led_count = rhapi.config.get('LED', 'LED_COUNT', as_int=True)
    led_rows = rhapi.config.get('LED', 'LED_ROWS', as_int=True)
    if (not Pil_avail_flag) and led_count > 1 and led_rows > 1:
        logger.info("Cannot support LED panel because 'pillow' module not installed")

    for led_effect in [
        LEDEffect(
            "Graph: RSSI (all)",
            rssiGraph, {
                'include': [LEDEvent.IDLE_DONE, LEDEvent.IDLE_READY, LEDEvent.IDLE_RACING],
                'exclude': [],
                'recommended': []
            },
            {
                'active_only': False,
                'serpentine': True,  # use serpentine pattern (single-row strip only)
                'use_enter_exit_ats': False  # use enter/exit-at values instead of node min/max
            },
            name='graphRSSI'
        ),
        LEDEffect(
            "Graph: RSSI (enabled)",
            rssiGraph, {
                'include': [LEDEvent.IDLE_DONE, LEDEvent.IDLE_READY, LEDEvent.IDLE_RACING],
                'exclude': [],
                'recommended': []
            }, {
                'active_only': True,
                'serpentine': True,  # use serpentine pattern (single-row strip only)
                'use_enter_exit_ats': False  # use enter/exit-at values instead of node min/max
            },
            name='graphRSSIActive'
        ),
        LEDEffect(
            "Graph: RSSI (first enabled)",  # only show first active node
            rssiGraph, {
                'include': [LEDEvent.IDLE_DONE, LEDEvent.IDLE_READY, LEDEvent.IDLE_RACING],
                'exclude': [],
                'recommended': []
            }, {
                'active_only': True,
                'single_node_only': True,
                'single_node_idx': -1,  # index of node to show (0=Node1), or -1 for first active
                'use_enter_exit_ats': False  # use enter/exit-at values instead of node min/max
            },
            name='graphRSSIFirst'
        )
    ]:
        args['register_fn'](led_effect)

def initialize(rhapi):
    rhapi.events.on(Evt.LED_INITIALIZE, register_handlers, {'RHAPI': rhapi})
