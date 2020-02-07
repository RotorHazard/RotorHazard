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

def led_on(strip, color, pattern=ColorPattern.SOLID):
    if pattern == ColorPattern.SOLID:
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
    elif pattern == ColorPattern.ALTERNATING:
        for i in range(strip.numPixels()):
            if i % 2 < 1:
                strip.setPixelColor(i, color)
            else:
                strip.setPixelColor(i, ColorVal.NONE)
    elif pattern == ColorPattern.TWO_OUT_OF_THREE:
        for i in range(strip.numPixels()):
            if i % 3 < 2:
                strip.setPixelColor(i, color)
            else:
                strip.setPixelColor(i, ColorVal.NONE)
    elif pattern == ColorPattern.MOD_SEVEN:
        for i in range(strip.numPixels()):
            if i % 7 < 1:
                strip.setPixelColor(i, color)
            else:
                strip.setPixelColor(i, ColorVal.NONE)
    elif pattern == ColorPattern.FOUR_ON_FOUR_OFF:
        for i in range(strip.numPixels()):
            if i % 8 < 4:
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
        gevent.sleep(args['time'])
        led_off(strip)

def clear(strip, config, args=None):
    led_off(strip)

def hold(strip, config, args=None):
    pass

# Effects adapted from work by Hans Luijten https://www.tweaking4all.com/hardware/arduino/adruino-led-strip-effects/

def colorWipe(strip, config, args=None):
    if args is None:
        return False

    for i in range(strip.numPixels()*2):
        strip.setPixelColor(i, args['color'])
        strip.show()
        gevent.sleep(args['speedDelay']/1000);

def blink(strip, config, args=None):
    '''
    defArgs = {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'decay': 0.5,
        'speedDelay': 0.3333,
        'onTime': 0,
        'iterations': 3
    }
    '''

    if args['decay']:
        # decay time = log(decay cutoff=10 / max brightness=256) / log(decay rate)
        decayTime = int(math.ceil(math.log(0.0390625) / math.log(args['decay'])))
    else:
        decayTime = 0

    # blink effect should never exceed 3Hz (health and safety)
    args['speedDelay'] = max(3-decayTime-args['onTime'], args['speedDelay'])

    for i in args['iterations']:
        led_on(strip, args['color'], args['pattern'])
        gevent.sleep(args['onTime']/1000);

        for t in range(decayTime):
            for j in range(strip.numPixels()):
                fadeToBlack(strip, j, args['decay']);
            strip.show()
        else:
            led_off(strip)

    gevent.sleep(args['speedDelay']/1000);

def sparkle(strip, config, args=None):
    if args is None:
        return False

    if args and 'iterations' in args:
        iterations = args['iterations']
    else:
        iterations = 100

    # decay time = log(decay cutoff=10 / max brightness=256) / log(decay rate)
    if args['decay']:
        decayTime = int(math.ceil(math.log(0.0390625) / math.log(args['decay'])))
    else:
        decayTime = 0

    for i in range(iterations + decayTime):
        # fade brightness all LEDs one step
        for j in range(strip.numPixels()):
            fadeToBlack(strip, j, args['decay']);

        # pick new pixel to light up
        if i <= iterations:
            pixel = random.randint(0, strip.numPixels()-1)
            strip.setPixelColor(pixel, args['color'])

        strip.show()
        gevent.sleep(args['speedDelay']/1000);

def meteor(strip, config, args=None):
    '''defArgs = {
        'color': ColorVal.WHITE,
        'decay': ,
        'speedDelay': 300
    }'''

    args = defArgs.extend(args)

    led_off(strip)

    for i in range(strip.numPixels()*2):

        # fade brightness all LEDs one step
        for j in range(strip.numPixels()):
            if not args['randomDecay'] or random.random() > 0.5:
                fadeToBlack(strip, j, args['decay'] );

        # draw meteor
        for j in range(args['meteorSize']):
            if i - j < strip.numPixels() and i - j >= 0:
                strip.setPixelColor(i-j, args['color'])

        strip.show()
        gevent.sleep(args['speedDelay']/1000);

def larsonScanner(strip, config, args=None):
    '''
    args = {
        'color': ColorVal.WHITE,
        'eyeSize': 4,
        'speedDelay': 10,
        'returnDelay': 50,
        'iterations': 3
    }
    '''

    for k in range(args['iterations']):
        for i in range(strip.numPixels()-args['eyeSize']-2):
            led_off(strip)
            strip.setPixelColor(i, dim(args['color'], 10))
            for j in range(1, args['eyeSize']):
                strip.setPixelColor(i+j, args['color'])
            strip.setPixelColor(i+args['eyeSize']+1, dim(args['color'], 10))
            strip.show()
            gevent.sleep(args['speedDelay']/1000);

        gevent.sleep(args['returnDelay']/1000);

        for i in range(strip.numPixels()-args['eyeSize']-2, 0, -1):
            led_off(strip)
            strip.setPixelColor(i, dim(args['color'], 10))
            for j in range(1, args['eyeSize']):
                strip.setPixelColor(i+j, args['color'])
            strip.setPixelColor(i+args['eyeSize']+1, dim(args['color'], 10))
            strip.show()
            gevent.sleep(args['speedDelay']/1000);

        gevent.sleep(args['returnDelay']/1000);


def dim(color, factor):
    r = color & 0x00ff0000 >> 16;
    g = color & 0x0000ff00 >> 8;
    b = color & 0x000000ff;

    r /= factor
    g /= factor
    b /= factor

    return Color(r, g, b)

def fadeToBlack(strip, ledNo, decay):
    oldColor = strip.getPixelColor(ledNo)
    r = oldColor & 0x00ff0000 >> 16;
    g = oldColor & 0x0000ff00 >> 8;
    b = oldColor & 0x000000ff;

    r = 0 if r <= 10 else int(r*decay)
    g = 0 if g <= 10 else int(g*decay)
    b = 0 if b <= 10 else int(b*decay)

    strip.setPixelColor(ledNo, Color(r,g,b))

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

    # blink
    manager.registerEffect("stripBlink", "Blink 3x", blink, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.SOLID,
        'decay': 0.5,
        'speedDelay': 0.3333,
        'onTime': 0,
        'iterations': 3
        })

    # meteor
    manager.registerEffect("stripMeteor", "Meteor Fall", meteor, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'meteorSize': 10,
        'decay': 0.75,
        'randomDecay': True,
        'speedDelay': 3
        })

    # sparkle
    manager.registerEffect("stripSparkle", "Sparkle", sparkle, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'decay': 0.95,
        'speedDelay': 100,
        'iterations': 100
        })

    # larson scanner
    manager.registerEffect("stripScanner", "Scanner", larsonScanner, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP], {
        'color': ColorVal.WHITE,
        'eyeSize': 4,
        'speedDelay': 10,
        'returnDelay': 50,
        'iterations': 3
        })

    # clear - permanently assigned to LEDEventManager.clear()
    manager.registerEffect("clear", "Turn Off", clear, [LEDEvent.NOCONTROL, LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP, LEDEvent.SHUTDOWN])

    # hold/no change
    manager.registerEffect("none", "No Change", hold, [LEDEvent.NOCONTROL, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP, LEDEvent.SHUTDOWN])
