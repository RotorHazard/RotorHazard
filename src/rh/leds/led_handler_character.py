'''LED visual effects'''

# to use this handler, run:
#    sudo apt-get install libjpeg-dev
#    sudo pip install pillow

from . import ColorVal, setPixels
from rh.events.eventmanager import Evt
from rh.events.led_event_manager import LEDEffect, LEDEvent
from rh.app.RHRace import RaceStatus
import gevent
from PIL import Image, ImageFont, ImageDraw
from monotonic import monotonic

FONT_PATH = 'rh/static/fonts'


def dataHandler(args):
    if 'data' in args:
        if args['data'] == 'staging':
            args['time'] = 0
            if 'hide_stage_timer' not in args or not args['hide_stage_timer']:
                if 'pi_starts_at_s' in args:
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
            for line in args['RACE'].results['by_race_time']:
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

    if 'color' in args:
        color = convertColor(args['color'])
    else:
        color = convertColor(ColorVal.WHITE)

    height = args['ledRows']
    width = strip.numPixels() // height
    im = Image.new('RGB', [width, height])
    draw = ImageDraw.Draw(im)

    use_small_flag = True
    if height >= 16:
        font = ImageFont.truetype(FONT_PATH+"/RotorHazardPanel16.ttf", 16)
        w, h = font.getsize(text)
        if w <= width - 1:
            use_small_flag = False
            h = 16

    if use_small_flag:
        font = ImageFont.truetype(FONT_PATH+"/RotorHazardPanel8.ttf", 8)
        w, h = font.getsize(text)
        h = 8

    draw.text((int((width-w)/2) + 1, int((height-h)/2)), text, font=font, fill=(color))

    img = im.rotate(90 * args['panelRotate'])

    setPixels(strip, img, args['invertedPanelRows'])
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
        color = convertColor(ColorVal.WHITE)

    height = args['ledRows']
    width = strip.numPixels() // height
    im = Image.new('RGB', [width, height])
    draw = ImageDraw.Draw(im)

    if height >= 16:
        font = ImageFont.truetype(FONT_PATH+"/RotorHazardPanel16.ttf", 16)
        w, h = font.getsize(text)
        h = 16
    else:
        font = ImageFont.truetype(FONT_PATH+"/RotorHazardPanel8.ttf", 8)
        w, h = font.getsize(text)
        h = 8

    draw_y = int((height-h)/2)

    for i in range(-width, w + width):
        draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
        draw.text((-i, draw_y), text, font=font, fill=(color))
        img = im.rotate(90 * args['panelRotate'])
        setPixels(strip, img, args['invertedPanelRows'])
        strip.show()
        gevent.sleep(10/1000.0)


def multiLapGrid(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    if 'RACE' in args:
        RACE = args['RACE']
    else:
        return False

    if args['RACE'].results and 'by_race_time' in args['RACE'].results:
        leaderboard = args['RACE'].results['by_race_time']
    else:
        return False

    height = args['ledRows']
    width = strip.numPixels() // height
    im = Image.new('RGB', [width, height])
    draw = ImageDraw.Draw(im)
    if height < 16:
        return False

    half_height = height/2
    half_width = width/2

    if height >= 32:
        font = ImageFont.truetype(FONT_PATH+"/RotorHazardPanel16.ttf", 16)
        font_h = 16
    else:
        font = ImageFont.truetype(FONT_PATH+"/RotorHazardPanel8.ttf", 8)
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
                if RACE.race_status == RaceStatus.DONE:
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

            draw.text((pos_x + 1, pos_y), text, font=font, fill=color)

    img = im.rotate(90 * args['panelRotate'])
    setPixels(strip, img, args['invertedPanelRows'])
    strip.show()


def clearPixels(strip):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, ColorVal.NONE)


def convertColor(color):
    return color >> 16, (color >> 8) % 256, color % 256


def discover(config, *args, **kwargs):
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
        'ledRows': config['LED_ROWS'],
        'panelRotate': config['PANEL_ROTATE'],
        'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
        'data': 'lap_number',
        'time': 5
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
        'ledRows': config['LED_ROWS'],
        'panelRotate': config['PANEL_ROTATE'],
        'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
        'data': 'lap_time',
        'time': 8
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
        'ledRows': config['LED_ROWS'],
        'panelRotate': config['PANEL_ROTATE'],
        'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
        'data': 'position',
        'time': 8
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
        'ledRows': config['LED_ROWS'],
        'panelRotate': config['PANEL_ROTATE'],
        'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
        'data': 'lap_time',
        'time': 2
        }
        ),
    LEDEffect(
        "textMessage",
        "Text Scroll: Message",
        scrollText, {
            'manual': False,
            'include': [Evt.MESSAGE_INTERRUPT, Evt.MESSAGE_STANDARD, Evt.STARTUP],
            'exclude': [Evt.ALL],
            'recommended': [Evt.MESSAGE_INTERRUPT, Evt.MESSAGE_STANDARD, Evt.STARTUP]
        }, {
        'ledRows': config['LED_ROWS'],
        'panelRotate': config['PANEL_ROTATE'],
        'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
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
        'ledRows': config['LED_ROWS'],
        'panelRotate': config['PANEL_ROTATE'],
        'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
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
        'ledRows': config['LED_ROWS'],
        'panelRotate': config['PANEL_ROTATE'],
        'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
        'data': 'staging',
        'time': 5
        }
        ),
    ]

    if (config['LED_ROWS'] >= 16):
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
                'ledRows': config['LED_ROWS'],
                'panelRotate': config['PANEL_ROTATE'],
                'invertedPanelRows': config['INVERTED_PANEL_ROWS'],
                'time': 4
                }
            )
        )

    return effects
