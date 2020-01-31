'''LED visual effects'''

from led_event_manager import LEDEvent, Color, ColorVal, ColorPattern
import gevent

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
        strip.setPixelColor(i, color_wheel((i) & 255))
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
        iterations = 1

    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color_wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        gevent.sleep(wait_ms/1000.0)

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

    def led_rainbow(strip, wait_ms=2, iterations=1):
        """Draw rainbow that fades across all pixels at once."""
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color_wheel((i) & 255))
        strip.show()
        gevent.sleep(wait_ms/1000.0)

def registerHandlers(manager):
    # register generic color change (does nothing without arguments)
    manager.registerEventHandler("stripColor", "Color/Pattern", showColor, [LEDEvent.MANUAL])
    manager.registerEventHandler("stripColorSolid", "Color/Pattern: (Pilot/Node) Solid", showColor, [LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT], {
        'pattern': ColorPattern.SOLID
        })
    manager.registerEventHandler("stripColor1_1", "Color/Pattern: (Pilot/Node) 1/1", showColor, [LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT], {
        'pattern': ColorPattern.ALTERNATING,
        'time': Timing.VTX_EXPIRE
        })

    # register specific colors needed for typical events
    manager.registerEventHandler("stripColorOrange2_1", "Color/Pattern: Orange 2/1", showColor, [LEDEvent.RACESTAGE], {
        'color': ColorVal.ORANGE,
        'pattern': ColorPattern.TWO_OUT_OF_THREE
        })
    manager.registerEventHandler("stripColorGreenSolid", "Color/Pattern: Green Solid", showColor, [LEDEvent.RACESTART], {
        'color': ColorVal.GREEN,
        'pattern': ColorPattern.SOLID,
        'time': Timing.START_EXPIRE
        })
    manager.registerEventHandler("stripColorWhite4_4", "Color/Pattern: White 4/4", showColor, [LEDEvent.RACEFINISH], {
        'color': ColorVal.WHITE,
        'pattern': ColorPattern.FOUR_ON_FOUR_OFF
        })
    manager.registerEventHandler("stripColorRedSolid", "Color/Pattern: Red Solid", showColor, [LEDEvent.RACESTOP], {
        'color': ColorVal.RED,
        'pattern': ColorPattern.SOLID
        })

    # rainbow cycle
    manager.registerEventHandler("rainbowCycle", "Color/Pattern: Rainbow", rainbowCycle, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP])

    # clear (available for all events, but also by specific manager function)
    manager.registerEventHandler("clear", "Turn Off", clear, [LEDEvent.STARTUP, LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP, LEDEvent.SHUTDOWN])

    # hold/no change
    manager.registerEventHandler("none", "No Change", hold, [LEDEvent.RACESTAGE, LEDEvent.CROSSINGENTER, LEDEvent.CROSSINGEXIT, LEDEvent.RACESTART, LEDEvent.RACEFINISH, LEDEvent.RACESTOP, LEDEvent.SHUTDOWN])
