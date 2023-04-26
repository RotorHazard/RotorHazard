'''LED visual effects'''

# to use this handler, run:
#    sudo apt-get install libjpeg-dev
#    sudo pip install pillow

import Config
from eventmanager import Evt
from led_event_manager import LEDEffect, LEDEvent, Color, ColorVal
from RHRace import RaceStatus
import gevent
from PIL import Image, ImageFont, ImageDraw
from monotonic import monotonic

def registerHandlers(args):
    if 'registerFn' in args:
        for led_effect in discover():
            args['registerFn'](led_effect)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('LED_Initialize', 'LED_register_character', registerHandlers, {}, 75, True)

def dataHandler(args):
    if 'data' in args:
        if args['data'] == 'staging':
            args['time'] = 0
            if not args['hide_stage_timer']:
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

            else:
                args['text'] = 'X'
                printCharacter(args)

        # standard methods
        elif args['data'] == 'lap_number':
            if args['lap']['lap_number'] > 0:
                args['text'] = args['lap']['lap_number']
            else:
                return False

        elif args['data'] == 'lap_time':
            args['text'] = '{0:.1f}'.format(args['lap']['lap_time'] / 1000)

        elif args['data'] == 'position':
            if 'results' in args and args['results']:
                result = args['results']
            elif 'RACE' in args and hasattr(args['RACE'], 'results'):
                result = args['RACE'].results
            else:
                return False

            if 'meta' in result and 'primary_leaderboard' in result['meta']: 
                leaderboard = result[result['meta']['primary_leaderboard']]
                if not len(leaderboard):
                    return False
            else:
                return False

            for line in leaderboard:
                if args['node_index'] == line['node']:
                    args['text'] = line['position']
                    break

        elif args['data'] == 'heat_id':
            args['text'] = args['heat_id']

        elif args['data'] == 'message':
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

    if 'color' in args and args['color']:
        color = convertColor(args['color'])
    else:
        color = convertColor(ColorVal.WHITE)

    panel = getPanelImg(strip)

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

    panel['draw'].text((int((panel['width']-w)/2), int((panel['height']-h)/2)), text, font=font, fill=(color))

    img = panel['im'].rotate(90 * Config.LED['PANEL_ROTATE'])

    setPixels(strip, img)
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

    if 'color' in args and args['color']:
        color = convertColor(args['color'])
    else:
        color = convertColor(ColorVal.WHITE)

    panel = getPanelImg(strip)

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

    if 'raceContext' in args:
        ctx = args['raceContext']

        RACE = ctx.race
        result = ctx.race.get_results()
    else:
        RACE = None
        return False

    if result and 'meta' in result and 'primary_leaderboard' in result['meta']: 
        leaderboard = result[result['meta']['primary_leaderboard']]
        if not len(leaderboard):
            return False
    else:
        return False

    panel = getPanelImg(strip)
    if panel['height'] < 16:
        return False

    half_height = panel['height']/2
    half_width = panel['width']/2

    if panel['height'] >= 32:
        font = ImageFont.truetype("static/fonts/RotorHazardPanel16.ttf", 16)
        font_h = 16
    else:
        font = ImageFont.truetype("static/fonts/RotorHazardPanel8.ttf", 8)
        font_h = 8

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
                if not RACE or RACE.race_status == RaceStatus.DONE:
                    text = str(line['laps'])
                else:
                    # first callsign character
                    text = line['callsign'][0]

            w, h = font.getsize(text)
            h = font_h
            color = convertColor(args['manager'].getDisplayColor(line['node'], from_result=True))

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
        "textLapNumber",
        "Text: Lap Count",
        dataHandler, {
            'manual': False,
            'include': [Evt.RACE_LAP_RECORDED],
            'exclude': [Evt.ALL],
            'recommended': [Evt.RACE_LAP_RECORDED]
        }, {
        'data': 'lap_number',
        'time': 4
        }
        ),
    LEDEffect(
        "textLapTime",
        "Text: Lap Time",
        dataHandler, {
            'manual': False,
            'include': [Evt.RACE_LAP_RECORDED],
            'exclude': [Evt.ALL],
            'recommended': [Evt.RACE_LAP_RECORDED]
        }, {
        'data': 'lap_time',
        'time': 4
        }
        ),
    LEDEffect(
        "textPosition",
        "Text: Position",
        dataHandler, {
            'manual': False,
            'include': [Evt.RACE_LAP_RECORDED],
            'exclude': [Evt.ALL],
            'recommended': [Evt.RACE_LAP_RECORDED]
        }, {
        'data': 'position',
        'time': 4
        }
        ),
    LEDEffect(
        "scrollLapTime",
        "Text Scroll: Lap Time",
        scrollText, {
            'manual': False,
            'include': [Evt.RACE_LAP_RECORDED],
            'exclude': [Evt.ALL],
            'recommended': [Evt.RACE_LAP_RECORDED]
        }, {
        'data': 'lap_time',
        'time': 2
        }
        ),
    LEDEffect(
        "textMessage",
        "Text Scroll: Message",
        scrollText, {
            'manual': False,
            'include': [Evt.MESSAGE_INTERRUPT, Evt.MESSAGE_STANDARD, Evt.STARTUP, Evt.CLUSTER_JOIN],
            'exclude': [Evt.ALL],
            'recommended': [Evt.MESSAGE_INTERRUPT, Evt.MESSAGE_STANDARD, Evt.STARTUP, Evt.CLUSTER_JOIN]
        }, {
        'data': 'message',
        'time': 0
        }
        ),
    LEDEffect(
        "textRaceWin",
        "Text Scroll: Race Winner",
        scrollText, {
            'manual': False,
            'include': [Evt.RACE_WIN],
            'exclude': [Evt.ALL],
            'recommended': [Evt.RACE_WIN]
        }, {
        'data': 'message',
        'time': 2
        }
        ),
    LEDEffect(
        "textStaging",
        "Text: Countdown",
        dataHandler, {
            'manual': False,
            'include': [Evt.RACE_STAGE],
            'exclude': [Evt.ALL],
            'recommended': [Evt.RACE_STAGE]
        }, {
        'data': 'staging',
        'time': 5
        }
        ),
    ]

    if (Config.LED['LED_ROWS'] >= 16):
        effects.append(
            LEDEffect(
                "textLapGrid",
                "Text: 4-Node Lap Count",
                multiLapGrid, {
                    'include': [LEDEvent.IDLE_DONE, LEDEvent.IDLE_RACING],
                    'recommended': [
                        Evt.RACE_STAGE,
                        Evt.RACE_LAP_RECORDED,
                        Evt.RACE_FINISH,
                        Evt.RACE_WIN,
                        Evt.RACE_STOP]
                }, {
                'time': 4
                }
            )
        )

    return effects
