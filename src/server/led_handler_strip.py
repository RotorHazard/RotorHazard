'''LED visual effects'''

from led_event_manager import LEDEvent, Color, ColorVal, ColorPattern
import gevent
import random
import math

nodeToColorArray = [ColorVal.BLUE, ColorVal.DARK_ORANGE, ColorVal.LIGHT_GREEN, ColorVal.YELLOW, \
                        ColorVal.PURPLE, ColorVal.PINK, ColorVal.MINT, ColorVal.SKY]

class Timing:
    VTX_EXPIRE = 4
    START_EXPIRE = 8

def led_on(strip, color, pattern=ColorPattern.SOLID, offset=0):
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

def theaterChase(strip, color, wait_ms=50, iterations=5):
    """Movie theater light style chaser animation."""
    led_on(strip, ColorVal.NONE)
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels()-q, 3):
                strip.setPixelColor(i+q, color)
            strip.show()
            gevent.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels()-q, 3):
                strip.setPixelColor(i+q, 0)

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

def rainbow(strip, config, args=None):
    """Draw rainbow that fades across all pixels at once."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color_wheel(int(i * 256 / strip.numPixels()) & 255))
    strip.show()

def rainbowCycle(strip, config, args=None):
    """Draw rainbow that uniformly distributes itself across all pixels."""
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

def showColor(strip, config, args=None):
    if args and 'color' in args:
        color = args['color']
    else:
        color = ColorVal.NONE

    if args and 'pattern' in args:
        pattern = args['pattern']
    else:
        pattern = ColorPattern.SOLID

    if args and 'nodeIndex' in args:
        led_on(strip, nodeToColorArray[args['nodeIndex']], pattern)
    else:
        led_on(strip, color, pattern)

    if 'time' in args and args['time'] is not None:
        gevent.sleep(float(args['time']))
        led_off(strip)

def clear(strip, config, args=None):
    led_off(strip)

def hold(strip, config, args=None):
    pass

# Effects adapted from work by Hans Luijten https://www.tweaking4all.com/hardware/arduino/adruino-led-strip-effects/

def colorWipe(strip, config, a={}):
    gevent.idle() # never time-critical

    args = {
        'color': ColorVal.WHITE,
        'speedDelay': 256,
    }
    args.update(a)

    args['speedDelay'] = args['speedDelay']/float(strip.numPixels()) # scale effect by strip length

    for i in range(strip.numPixels()):
        strip.setPixelColor(i, args['color'])
        strip.show()
        gevent.sleep(args['speedDelay']/1000.0)

def fade(strip, config, a={}):
    args = {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'steps': 25,
        'speedDelay': 10,
        'onTime': 250,
        'offTime': 250,
        'iterations': 1
    }
    args.update(a)

    led_off(strip)

    if 'outSteps' not in args:
        args['outSteps'] = args['steps']

    # effect should never exceed 3Hz (prevent seizures)
    args['offTime'] = min(333-((args['steps']*args['speedDelay'])+(args['outSteps']*args['speedDelay'])+args['onTime']), args['offTime'])

    for i in range(args['iterations']):
        # fade in
        if args['steps']:
            led_off(strip)
            gevent.idle() # never time-critical
            for j in range(0, args['steps'], 1):
                c = dim(args['color'], j/float(args['steps']))
                led_on(strip, c, args['pattern'])
                strip.show()
                gevent.sleep(args['speedDelay']/1000.0);
            else:
                led_on(strip, args['color'], args['pattern'])

            led_on(strip, args['color'], args['pattern'])
            gevent.sleep(args['onTime']/1000.0);

        # fade out
        if args['outSteps']:
            led_on(strip, args['color'], args['pattern'])
            for j in range(args['outSteps'], 0, -1):
                c = dim(args['color'], j/float(args['outSteps']))
                led_on(strip, c, args['pattern'])
                strip.show()
                gevent.sleep(args['speedDelay']/1000.0);

            else:
                led_off(strip)

            led_off(strip)

        gevent.sleep(args['offTime']/1000.0);

def sparkle(strip, config, a={}):
    args = {
        'color': ColorVal.WHITE,
        'chance': 1.0,
        'decay': 0.95,
        'speedDelay': 100,
        'iterations': 100
    }
    args.update(a)

    gevent.idle() # never time-critical

    # decay time = log(decay cutoff=10 / max brightness=256) / log(decay rate)
    if args['decay']:
        decaySteps = int(math.ceil(math.log(0.00390625) / math.log(args['decay'])))
    else:
        decaySteps = 0

    led_off(strip)

    for i in range(args['iterations'] + decaySteps):
        # fade brightness all LEDs one step
        for j in range(strip.numPixels()):
            c = strip.getPixelColor(j)
            strip.setPixelColor(j, dim(c, args['decay']))

        # pick new pixels to light up
        if i < args['iterations']:
            for px in range(strip.numPixels()):
                if random.random() < float(args['chance']) / strip.numPixels():
                    # scale effect by strip length
                    strip.setPixelColor(px, args['color'])

        strip.show()
        gevent.sleep(args['speedDelay']/1000.0);

def meteor(strip, config, a={}):
    args = {
        'color': ColorVal.WHITE,
        'meteorSize': 10,
        'decay': 0.75,
        'randomDecay': True,
        'speedDelay': 1
    }
    args.update(a)

    gevent.idle() # never time-critical

    led_off(strip)

    for i in range(strip.numPixels()*2):

        # fade brightness all LEDs one step
        for j in range(strip.numPixels()):
            if not args['randomDecay'] or random.random() > 0.5:
                c = strip.getPixelColor(j)
                strip.setPixelColor(j, dim(c, args['decay']))

        # draw meteor
        for j in range(args['meteorSize']):
            if i - j < strip.numPixels() and i - j >= 0:
                strip.setPixelColor(i-j, args['color'])

        strip.show()
        gevent.sleep(args['speedDelay']/1000.0)

def larsonScanner(strip, config, a={}):
    args = {
        'color': ColorVal.WHITE,
        'eyeSize': 4,
        'speedDelay': 256,
        'returnDelay': 50,
        'iterations': 3
    }
    args.update(a)

    args['speedDelay'] = args['speedDelay']/float(strip.numPixels()) # scale effect by strip length

    gevent.idle() # never time-critical

    led_off(strip)

    for k in range(args['iterations']):
        for i in range(strip.numPixels()-args['eyeSize']-1):
            strip.setPixelColor(i-1, ColorVal.NONE)

            strip.setPixelColor(i, dim(args['color'], 0.25))
            for j in range(args['eyeSize']):
                strip.setPixelColor(i+j+1, args['color'])
            strip.setPixelColor(i+args['eyeSize']+1, dim(args['color'], 0.25))
            strip.show()
            gevent.sleep(args['speedDelay']/1000.0)

        gevent.sleep(args['returnDelay']/1000.0)

        for i in range(strip.numPixels()-args['eyeSize']-2, -1, -1):
            if i < strip.numPixels()-args['eyeSize']-2:
                strip.setPixelColor(i+args['eyeSize']+2, ColorVal.NONE)

            strip.setPixelColor(i, dim(args['color'], 0.25))
            for j in range(args['eyeSize']):
                strip.setPixelColor(i+j+1, args['color'])
            strip.setPixelColor(i+args['eyeSize']+1, dim(args['color'], 0.25))
            strip.show()
            gevent.sleep(args['speedDelay']/1000.0)

        gevent.sleep(args['returnDelay']/1000.0)

def dim(color, decay):
    r = (color & 0x00ff0000) >> 16;
    g = (color & 0x0000ff00) >> 8;
    b = (color & 0x000000ff);

    r = 0 if r <= 1 else int(r*decay)
    g = 0 if g <= 1 else int(g*decay)
    b = 0 if b <= 1 else int(b*decay)

    return Color(int(r), int(g), int(b))

def registerEffects(manager):

    # register generic color change (does nothing without arguments)
    manager.registerEffect("stripColor", "Color/Pattern (Args)", showColor, [LEDEvent.NOCONTROL])
    manager.registerEffect("stripColorSolid", "Color/Pattern: (Pilot/Node) Solid", showColor, [LEDEvent.NOCONTROL, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT], {
        'pattern': ColorPattern.SOLID
        })
    manager.registerEffect("stripColor1_1", "Color/Pattern: (Pilot/Node) 1/1", showColor, [LEDEvent.NOCONTROL, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT], {
        'pattern': ColorPattern.ALTERNATING,
        'time': Timing.VTX_EXPIRE
        })
    manager.registerEffect("stripWipe", "Color Wipe: (Pilot/Node)", colorWipe, [LEDEvent.NOCONTROL, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT], {
        'color': ColorVal.WHITE,
        'speedDelay': 3
        })

    # register specific colors needed for typical events
    manager.registerEffect("stripColorOrange2_1", "Color/Pattern: Orange 2/1", showColor, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP, LEDEvent.SHUTDOWN], {
        'color': ColorVal.ORANGE,
        'pattern': ColorPattern.TWO_OUT_OF_THREE
        })
    manager.registerEffect("stripColorGreenSolid", "Color/Pattern: Green Solid", showColor, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP, LEDEvent.SHUTDOWN], {
        'color': ColorVal.GREEN,
        'pattern': ColorPattern.SOLID,
        'time': Timing.START_EXPIRE
        })
    manager.registerEffect("stripColorWhite4_4", "Color/Pattern: White 4/4", showColor, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP, LEDEvent.SHUTDOWN], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.FOUR_ON_FOUR_OFF
        })
    manager.registerEffect("stripColorRedSolid", "Color/Pattern: Red Solid", showColor, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP, LEDEvent.SHUTDOWN], {
        'color': ColorVal.RED,
        'pattern': ColorPattern.SOLID
        })

    # rainbow
    manager.registerEffect("rainbow", "Color/Pattern: Rainbow", rainbow, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP])
    manager.registerEffect("rainbowCycle", "Color/Pattern: Rainbow Cycle", rainbowCycle, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'offWhenDone': True
        })

    # wipe
    manager.registerEffect("stripWipe", "Wipe", colorWipe, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'speedDelay': 256,
        })

    # fade
    manager.registerEffect("stripFadeIn", "Fade In", fade, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'steps': 50,
        'outSteps': 0,
        'speedDelay': 10,
        'onTime': 0,
        'offTime': 0,
        'iterations': 1
    })
    manager.registerEffect("stripPulse", "Pulse 3x", fade, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'steps': 10,
        'outSteps': 10,
        'speedDelay': 1,
        'onTime': 10,
        'offTime': 10,
        'iterations': 3
    })
    manager.registerEffect("stripFadeOut", "Fade Out", fade, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'steps': 10,
        'outSteps': 128,
        'speedDelay': 1,
        'onTime': 0,
        'offTime': 0,
        'iterations': 1
    })

    # blink
    manager.registerEffect("stripBlink", "Blink 3x", fade, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'steps': 1,
        'speedDelay': 1,
        'onTime': 100,
        'offTime': 100,
        'iterations': 3
        })

    # sparkle
    manager.registerEffect("stripSparkle", "Sparkle", sparkle, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'chance': 1.0,
        'decay': 0.95,
        'speedDelay': 10,
        'iterations': 30
        })

    # meteor
    manager.registerEffect("stripMeteor", "Meteor Fall", meteor, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'meteorSize': 10,
        'decay': 0.75,
        'randomDecay': True,
        'speedDelay': 1
        })

    # larson scanner
    manager.registerEffect("stripScanner", "Scanner", larsonScanner, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'eyeSize': 4,
        'speedDelay': 256,
        'returnDelay': 50,
        'iterations': 3
        })

    # clear - permanently assigned to LEDEventManager.clear()
    manager.registerEffect("clear", "Turn Off", clear, [LEDEvent.NOCONTROL, LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP, LEDEvent.SHUTDOWN])

    # hold/no change
    manager.registerEffect("none", "No Change", hold, [LEDEvent.NOCONTROL, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP, LEDEvent.SHUTDOWN])
