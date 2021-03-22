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
            args['text'] = '{0:.1f}'.format(args['lap']['lap_time'])

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
        color = args['color']
    else:
        return False

    color_r = color >> 16
    color_g = (color >> 8) % 256
    color_b = color % 256

    panelWidth = int(strip.numPixels() / Config.LED['LED_ROWS'])
    panelHeight = Config.LED['LED_ROWS']

    im = Image.new('RGB', [panelWidth, panelHeight])

    draw = ImageDraw.Draw(im)

    use_small_flag = True
    if panelHeight >= 16:
        font = ImageFont.truetype("static/fonts/RotorHazardPanel16.ttf", 16)
        w, h = font.getsize(text)
        if w <= panelWidth - 1:
            use_small_flag = False

    if use_small_flag:
        font = ImageFont.truetype("static/fonts/RotorHazardPanel8.ttf", 8)
        w, h = font.getsize(text)

    draw.text((int((panelWidth-w)/2) + 1, 0), text, font=font, fill=(color_r, color_g, color_b))

    def setPixels(img):
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

    img = im.rotate(90 * Config.LED['PANEL_ROTATE'])

    setPixels(img)
    strip.show()

    if 'time' in args and args['time'] is not None:
        gevent.sleep(float(args['time']))
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, ColorVal.NONE)
        strip.show()

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
        'time': 5
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
        'time': 5
        }
        ),
    LEDEffect(
        "textMessage",
        "Text: Message",
        dataHandler,
        [Evt.MESSAGE_INTERRUPT],
        {
        'color': ColorVal.WHITE,
        'data': 'message',
        'time': 5
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
    ]
