'''LED visual effects'''

from eventmanager import Evt
from led_event_manager import LEDEffect, LEDEvent, Color, ColorVal, ColorPattern
import gevent
import random
import math

class Timing:
    VTX_EXPIRE = 4
    START_EXPIRE = 8

def led_on(strip, color=ColorVal.WHITE, pattern=ColorPattern.SOLID, offset=0):
    if pattern == ColorPattern.SOLID:
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
    else:
        patternlength = sum(pattern)

        for i in range(strip.numPixels()):
            if (i+offset) % patternlength < pattern[0]:
                strip.setPixelColor(i, color)
            else:
                strip.setPixelColor(i, ColorVal.NONE)

    strip.show()

def led_off(strip):
    led_on(strip, ColorVal.NONE)

def chase(args):
    """Movie theater light style chaser animation."""
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    a = {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.ONE_OF_THREE,
        'speedDelay': 50,
        'iterations': 5,
        'offWhenDone': True
    }
    a.update(args)

    led_off(strip)

    for i in range(a['iterations'] * sum(a['pattern'])):
        led_on(strip, a['color'], a['pattern'], i)
        gevent.sleep(a['speedDelay']/1000.0)

    if a['offWhenDone']:
        led_off(strip)

def color_wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow(args):
    """Draw rainbow that fades across all pixels at once."""
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color_wheel(int(i * 256 / strip.numPixels()) & 255))
    strip.show()

def rainbowCycle(args):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    if args and 'wait_ms' in args:
        wait_ms = args['wait_ms']
    else:
        wait_ms = 2

    if args and 'iterations' in args:
        iterations = args['iterations']
    else:
        iterations = 3

    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color_wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        gevent.sleep(wait_ms/1000.0)

    if 'offWhenDone' in args and args['offWhenDone']:
        led_off(strip)

'''
def theaterChaseRainbow(strip, wait_ms=25):
    """Rainbow movie theater light style chaser animation."""
    led_on(strip, ColorVal.NONE)
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels()-q, 3):
                strip.setPixelColor(i+q, color_wheel((i+j) % 255))
            strip.show()
            gevent.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels()-q, 3):
                strip.setPixelColor(i+q, 0)
'''

def showColor(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    if 'color' in args:
        color = args['color']
    else:
        color = ColorVal.WHITE

    if 'pattern' in args:
        pattern = args['pattern']
    else:
        pattern = ColorPattern.SOLID

    led_on(strip, color, pattern)

    if 'time' in args and args['time'] is not None:
        gevent.sleep(float(args['time']))
        led_off(strip)

def clear(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    led_off(strip)

# Effects adapted from work by Hans Luijten https://www.tweaking4all.com/hardware/arduino/adruino-led-strip-effects/

def colorWipe(args):
    gevent.idle() # never time-critical

    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    a = {
        'color': ColorVal.WHITE,
        'speedDelay': 256,
    }
    a.update(args)

    a['speedDelay'] = a['speedDelay']/float(strip.numPixels()) # scale effect by strip length

    for i in range(strip.numPixels()):
        strip.setPixelColor(i, a['color'])
        strip.show()
        gevent.sleep(a['speedDelay']/1000.0)

def fade(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    a = {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'steps': 25,
        'speedDelay': 10,
        'onTime': 250,
        'offTime': 250,
        'iterations': 1
    }
    a.update(args)

    led_off(strip)

    if 'outSteps' not in a:
        a['outSteps'] = a['steps']

    # effect should never exceed 3Hz (prevent seizures)
    a['offTime'] = min(333-((a['steps']*a['speedDelay'])+(a['outSteps']*a['speedDelay'])+a['onTime']), a['offTime'])

    for i in range(a['iterations']):
        # fade in
        if a['steps']:
            led_off(strip)
            gevent.idle() # never time-critical
            for j in range(0, a['steps'], 1):
                c = dim(a['color'], j/float(a['steps']))
                led_on(strip, c, a['pattern'])
                strip.show()
                gevent.sleep(a['speedDelay']/1000.0);
            else:
                led_on(strip, a['color'], a['pattern'])

            led_on(strip, a['color'], a['pattern'])
            gevent.sleep(a['onTime']/1000.0);

        # fade out
        if a['outSteps']:
            led_on(strip, a['color'], a['pattern'])
            for j in range(a['outSteps'], 0, -1):
                c = dim(a['color'], j/float(a['outSteps']))
                led_on(strip, c, a['pattern'])
                strip.show()
                gevent.sleep(a['speedDelay']/1000.0);

            else:
                led_off(strip)

            led_off(strip)

        gevent.sleep(a['offTime']/1000.0);

def sparkle(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    a = {
        'color': ColorVal.WHITE,
        'chance': 1.0,
        'decay': 0.95,
        'speedDelay': 100,
        'iterations': 100
    }
    a.update(args)

    gevent.idle() # never time-critical

    # decay time = log(decay cutoff=10 / max brightness=256) / log(decay rate)
    if a['decay']:
        decaySteps = int(math.ceil(math.log(0.00390625) / math.log(a['decay'])))
    else:
        decaySteps = 0

    led_off(strip)

    for i in range(a['iterations'] + decaySteps):
        # fade brightness all LEDs one step
        for j in range(strip.numPixels()):
            c = strip.getPixelColor(j)
            strip.setPixelColor(j, dim(c, a['decay']))

        # pick new pixels to light up
        if i < a['iterations']:
            for px in range(strip.numPixels()):
                if random.random() < float(a['chance']) / strip.numPixels():
                    # scale effect by strip length
                    strip.setPixelColor(px, a['color'])

        strip.show()
        gevent.sleep(a['speedDelay']/1000.0);

def meteor(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    a = {
        'color': ColorVal.WHITE,
        'meteorSize': 10,
        'decay': 0.75,
        'randomDecay': True,
        'speedDelay': 1
    }
    a.update(args)

    gevent.idle() # never time-critical

    led_off(strip)

    for i in range(strip.numPixels()*2):

        # fade brightness all LEDs one step
        for j in range(strip.numPixels()):
            if not a['randomDecay'] or random.random() > 0.5:
                c = strip.getPixelColor(j)
                strip.setPixelColor(j, dim(c, a['decay']))

        # draw meteor
        for j in range(a['meteorSize']):
            if i - j < strip.numPixels() and i - j >= 0:
                strip.setPixelColor(i-j, a['color'])

        strip.show()
        gevent.sleep(a['speedDelay']/1000.0)

def larsonScanner(args):
    if 'strip' in args:
        strip = args['strip']
    else:
        return False

    a = {
        'color': ColorVal.WHITE,
        'eyeSize': 4,
        'speedDelay': 256,
        'returnDelay': 50,
        'iterations': 3
    }
    a.update(args)

    a['speedDelay'] = a['speedDelay']/float(strip.numPixels()) # scale effect by strip length

    gevent.idle() # never time-critical

    led_off(strip)

    for k in range(a['iterations']):
        for i in range(strip.numPixels()-a['eyeSize']-1):
            strip.setPixelColor(i-1, ColorVal.NONE)

            strip.setPixelColor(i, dim(a['color'], 0.25))
            for j in range(a['eyeSize']):
                strip.setPixelColor(i+j+1, a['color'])
            strip.setPixelColor(i+a['eyeSize']+1, dim(a['color'], 0.25))
            strip.show()
            gevent.sleep(a['speedDelay']/1000.0)

        gevent.sleep(a['returnDelay']/1000.0)

        for i in range(strip.numPixels()-a['eyeSize']-2, -1, -1):
            if i < strip.numPixels()-a['eyeSize']-2:
                strip.setPixelColor(i+a['eyeSize']+2, ColorVal.NONE)

            strip.setPixelColor(i, dim(a['color'], 0.25))
            for j in range(a['eyeSize']):
                strip.setPixelColor(i+j+1, a['color'])
            strip.setPixelColor(i+a['eyeSize']+1, dim(a['color'], 0.25))
            strip.show()
            gevent.sleep(a['speedDelay']/1000.0)

        gevent.sleep(a['returnDelay']/1000.0)

def dim(color, decay):
    r = (color & 0x00ff0000) >> 16;
    g = (color & 0x0000ff00) >> 8;
    b = (color & 0x000000ff);

    r = 0 if r <= 1 else int(r*decay)
    g = 0 if g <= 1 else int(g*decay)
    b = 0 if b <= 1 else int(b*decay)

    return Color(int(r), int(g), int(b))

def discover(*args, **kwargs):
    return [
    # color
    LEDEffect("stripColor", "Color/Pattern (Args)", showColor, [LEDEvent.NOCONTROL]),
    LEDEffect("stripColorSolid", "Solid", showColor, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'pattern': ColorPattern.SOLID
        }),
    LEDEffect("stripColor1_1", "Pattern 1-1", showColor, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'pattern': ColorPattern.ALTERNATING
        }),

    LEDEffect("stripColorSolid_4s", "Solid (4s expire)", showColor, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'pattern': ColorPattern.SOLID,
        'time': Timing.VTX_EXPIRE
        }),
    LEDEffect("stripColor1_1_4s", "Pattern 1-1 (4s expire)", showColor, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'pattern': ColorPattern.ALTERNATING,
        'time': Timing.VTX_EXPIRE
        }),


    # register specific items needed for typical events
    LEDEffect("stripColorOrange2_1", "Pattern 2-1 / Orange", showColor, [Evt.STARTUP, Evt.RACE_STAGE, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR, Evt.SHUTDOWN], {
        'color': ColorVal.ORANGE,
        'pattern': ColorPattern.TWO_OUT_OF_THREE
        }),
    LEDEffect("stripColorGreenSolid", "Solid / Green", showColor, [Evt.STARTUP, Evt.RACE_STAGE, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR, Evt.SHUTDOWN], {
        'color': ColorVal.GREEN,
        'pattern': ColorPattern.SOLID,
        'time': Timing.START_EXPIRE
        }),
    LEDEffect("stripColorWhite4_4", "Pattern 4-4", showColor, [Evt.STARTUP, Evt.RACE_STAGE, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR, Evt.SHUTDOWN], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.FOUR_ON_FOUR_OFF
        }),
    LEDEffect("stripColorRedSolid", "Solid / Red", showColor, [Evt.STARTUP, Evt.RACE_STAGE, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR, Evt.SHUTDOWN], {
        'color': ColorVal.RED,
        'pattern': ColorPattern.SOLID
        }),

    # chase
    LEDEffect("stripChase", "Chase Pattern 1-2", chase, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.ONE_OF_THREE,
        'speedDelay': 50,
        'iterations': 5,
        'offWhenDone': True
        }),

    # rainbow
    LEDEffect("rainbow", "Rainbow", rainbow, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR]),
    LEDEffect("rainbowCycle", "Rainbow Cycle", rainbowCycle, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'offWhenDone': True
        }),

    # wipe
    LEDEffect("stripWipe", "Wipe", colorWipe, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'color': ColorVal.WHITE,
        'speedDelay': 3,
        }),

    # fade
    LEDEffect("stripFadeIn", "Fade In", fade, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'steps': 50,
        'outSteps': 0,
        'speedDelay': 10,
        'onTime': 0,
        'offTime': 0,
        'iterations': 1
        }),
    LEDEffect("stripPulse", "Pulse 3x", fade, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'steps': 10,
        'outSteps': 10,
        'speedDelay': 1,
        'onTime': 10,
        'offTime': 10,
        'iterations': 3
        }),
    LEDEffect("stripFadeOut", "Fade Out", fade, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'steps': 10,
        'outSteps': 128,
        'speedDelay': 1,
        'onTime': 0,
        'offTime': 0,
        'iterations': 1
        }),

    # blink
    LEDEffect("stripBlink", "Blink 3x", fade, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'steps': 1,
        'speedDelay': 1,
        'onTime': 100,
        'offTime': 100,
        'iterations': 3
        }),

    # sparkle
    LEDEffect("stripSparkle", "Sparkle", sparkle, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'color': ColorVal.WHITE,
        'chance': 1.0,
        'decay': 0.95,
        'speedDelay': 10,
        'iterations': 50
        }),

    # meteor
    LEDEffect("stripMeteor", "Meteor Fall", meteor, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'color': ColorVal.WHITE,
        'meteorSize': 10,
        'decay': 0.75,
        'randomDecay': True,
        'speedDelay': 1
        }),

    # larson scanner
    LEDEffect("stripScanner", "Scanner", larsonScanner, [Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR], {
        'color': ColorVal.WHITE,
        'eyeSize': 4,
        'speedDelay': 256,
        'returnDelay': 50,
        'iterations': 3
        }),

    # clear - permanently assigned to LEDEventManager.clear()
    LEDEffect("clear", "Turn Off", clear, [LEDEvent.NOCONTROL, Evt.STARTUP, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_LAP_RECORDED, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR, Evt.SHUTDOWN, Evt.HEAT_SET, Evt.MESSAGE_INTERRUPT])
    ]
