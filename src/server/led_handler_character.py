'''LED visual effects'''

# to use this handler, run:
#    sudo apt-get install libjpeg-dev
#    sudo pip install pillow

import Config
from eventmanager import Evt
from led_event_manager import LEDEffect, Color, ColorVal
import gevent
from PIL import Image, ImageFont, ImageDraw
from monotonic import monotonic

def dataHandler(args):
    if 'data' in args:
        if args['data'] == 'staging':
            if not args['hide_stage_timer']:
                args['time'] = None
                start_time = args['pi_starts_at_s']

                while monotonic() < start_time:
                    diff = start_time - monotonic()
                    diff_to_s = diff % 1
                    if diff:
                        gevent.sleep(diff_to_s)
                        args['text'] = int(diff)
                        printCharacter(args)
                    else:
                        break

            return None

        # standard methods
        if args['data'] == 'lap_number':
            if args['lap']['lap_number'] > 0:
                args['text'] = args['lap']['lap_number']
            else:
                return False

        if args['data'] == 'lap_time':
            args['text'] = '{0:.1f}'.format(args['lap']['lap_time'] / 1000)

        if args['data'] == 'heat_id':
            args['text'] = args['heat_id']

        if args['data'] == 'message':
            args['text'] = args['message']

        printCharacter(args)
    else:
        return False

def printCharacter(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    if 'text' in args:
        text = str(args['text'])
    else:
        return False

    if 'color' in args:
        color = convertColor(args['color'])
    else:
        return False

    panel = getPanelImg(strip, Config)

    use_small_flag = True
    if panel['height'] >= 16:
        font = ImageFont.truetype("static/fonts/RotorHazardPanel16.ttf", 16)
        w, h = font.getsize(text)
        if w <= panel['width'] - 1:
            use_small_flag = False
            h = 16

    if use_small_flag:
        font = ImageFont.truetype("static/fonts/RotorHazardPanel8.ttf", 8)
        w, h = font.getsize(text)
        h = 8

    panel['draw'].text((int((panel['width']-w)/2) + 1, int((panel['height']-h)/2)), text, font=font, fill=(color))

    img = panel['im'].rotate(90 * Config.LED['PANEL_ROTATE'])

    setPixels(strip, img)
    strip.show()

    if 'time' in args and args['time'] is not None:
        gevent.sleep(float(args['time']))
        clearPixels(strip)
        strip.show()

def scrollText(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    if args['data'] == 'message':
        text = str(args['message'])
    elif args['data'] == 'lap_time':
        text = str(args['lap']['lap_time_formatted'])
    else:
        return False

    if 'color' in args:
        color = convertColor(args['color'])
    else:
        return False

    panel = getPanelImg(strip, Config)

    if panel['height'] >= 16:
        font = ImageFont.truetype("static/fonts/RotorHazardPanel16.ttf", 16)
        w, h = font.getsize(text)
        h = 16
    else:
        font = ImageFont.truetype("static/fonts/RotorHazardPanel8.ttf", 8)
        w, h = font.getsize(text)
        h = 8

    draw_y = int((panel['height']-h)/2)

    for i in range(-panel['width'], w + panel['width']):
        panel['draw'].rectangle((0, 0, panel['width'], panel['height']), fill=(0, 0, 0))
        panel['draw'].text((-i, draw_y), text, font=font, fill=(color))
        img = panel['im'].rotate(90 * Config.LED['PANEL_ROTATE'])
        setPixels(strip, img)
        strip.show()
        gevent.sleep(10/1000.0)

def multiLapGrid(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    if 'RHData' in args:
        RHData = args['RHData']
    else:
        return False

    if 'results' in args:
        results = args['results']
    else:
        return False

    panel = getPanelImg(strip, Config)
    if panel['height'] < 16:
        return False

    half_height = panel['height']/2
    half_width = panel['width']/2

    font = ImageFont.truetype("static/fonts/RotorHazardPanel8.ttf", 8)

    leaderboard = results['by_race_time']

    active_nodes = []
    for line in leaderboard:
        active_nodes.append(line['node'])

    active_nodes.sort()

    for line in leaderboard:
        if line['node'] < 4:
            if line['laps']:
                if line['laps'] <= 19:
                    text = str(line['laps'])
                else:
                    text = '+'
            else:
                text = line['callsign'][0]

            w, h = font.getsize(text)
            h = 8
            color = RHData.get_option('colorNode_' + str(line['node']), '#ffffff')

            # draw positions
            if active_nodes.index(line['node']) == 0:
                pos_x = int((half_width - w)/2)
                pos_y = int(((half_height) - h)/2)
            elif active_nodes.index(line['node']) == 1:
                pos_x = int(((half_width - w)/2) + half_width)
                pos_y = int(((half_height) - h)/2)
            elif active_nodes.index(line['node']) == 2:
                pos_x = int((half_width - w)/2)
                pos_y = int((((half_height) - h)/2) + half_height)
            elif active_nodes.index(line['node']) == 3:
                pos_x = int(((half_width - w)/2) + half_width)
                pos_y = int((((half_height) - h)/2) + half_height)

            panel['draw'].text((pos_x + 1, pos_y), text, font=font, fill=color)

    img = panel['im'].rotate(90 * Config.LED['PANEL_ROTATE'])
    setPixels(strip, img)
    strip.show()

def getPanelImg(strip, Config):
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
    return [
    LEDEffect(
        "textLapNumber",
        "Text: Lap Count",
        dataHandler,
        [Evt.RACE_LAP_RECORDED],
        {
        'color': ColorVal.WHITE,
        'data': 'lap_number',
        'time': 5
        }
        ),
    LEDEffect(
        "textLapTime",
        "Text: Lap Time",
        dataHandler,
        [Evt.RACE_LAP_RECORDED],
        {
        'color': ColorVal.WHITE,
        'data': 'lap_time',
        'time': 8
        }
        ),
    LEDEffect(
        "scrollLapTime",
        "Text Scroll: Lap Time",
        scrollText,
        [Evt.RACE_LAP_RECORDED],
        {
        'color': ColorVal.WHITE,
        'data': 'lap_time'
        }
        ),
    LEDEffect(
        "textHeat",
        "Text: Heat ID",
        dataHandler,
        [Evt.HEAT_SET],
        {
        'color': ColorVal.WHITE,
        'data': 'heat_id',
        'time': None
        }
        ),
    LEDEffect(
        "textMessage",
        "Text Scroll: Message",
        scrollText,
        [Evt.MESSAGE_INTERRUPT],
        {
        'color': ColorVal.WHITE,
        'data': 'message'
        }
        ),
    LEDEffect(
        "textRaceWin",
        "Text Scroll: Race Winner",
        scrollText,
        [Evt.RACE_WIN],
        {
        'color': ColorVal.WHITE,
        'data': 'message'
        }
        ),
    LEDEffect(
        "textStaging",
        "Text: Countdown",
        dataHandler,
        [Evt.RACE_STAGE],
        {
        'color': ColorVal.WHITE,
        'data': 'staging',
        'time': 5
        }
        ),
    LEDEffect(
        "textLapGrid",
        "Text: 4-Node Lap Count",
        multiLapGrid,
        [Evt.RACE_STAGE, Evt.RACE_START, Evt.RACE_LAP_RECORDED, Evt.RACE_FINISH, Evt.RACE_WIN, Evt.RACE_STOP],
        {}
        ),
    ]
