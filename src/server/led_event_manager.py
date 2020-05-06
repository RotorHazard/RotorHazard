'''
LED event manager
Wires events to handlers
'''

import gevent
from eventmanager import Evt
from UserDict import UserDict

class LEDEventManager:
    processEventObj = gevent.event.Event()

    events = {}
    eventEffects = {}
    eventThread = None

    def __init__(self, eventmanager, strip):
        self.Events = eventmanager
        self.strip = strip

        # hold
        self.registerEffect(LEDEffect("hold", "Hold", lambda *args: None,
            [LEDEvent.NOCONTROL, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR, Evt.SHUTDOWN]))

        # do nothing
        self.registerEffect(LEDEffect("none", "No Change", lambda *args: None, [LEDEvent.NOCONTROL, Evt.RACE_STAGE, Evt.CROSSING_ENTER, Evt.CROSSING_EXIT, Evt.RACE_START, Evt.RACE_FINISH, Evt.RACE_STOP, Evt.LAPS_CLEAR, Evt.SHUTDOWN]))


    def isEnabled(self):
        return True

    def registerEffect(self, effect):
        self.eventEffects[effect['name']] = effect
        return True

    def getRegisteredEffects(self):
        return self.eventEffects

    def getEventEffect(self, event):
        if event in self.events:
            return self.events[event]
        else:
            return False

    def setEventEffect(self, event, name):
        self.events[event] = name

        args = self.eventEffects[name]['defaultArgs']
        if args is None:
            args = {}

        args.update({
            'strip': self.strip,
            })

        if event in [Evt.SHUTDOWN]:
            # event is direct (blocking)
            self.Events.on(event, 'LED', self.eventEffects[name]['handlerFn'], args, 50)
        else:
            # event is normal (threaded/non-blocking)
            self.Events.on(event, 'LED', self.eventEffects[name]['handlerFn'], args, 150)
        return True

    def clear(self):
        self.eventEffects['clear']['handlerFn'](self.strip)

class NoLEDManager():
    def __init__(self):
        pass

    def isEnabled(self):
        return False

    def __getattr__(self, *args, **kwargs):
        def nothing(*args, **kwargs):
            return False
        return nothing

'''
Generic data structures for working with LED commands
'''

def Color(red, green, blue):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return (red << 16) | (green << 8) | blue

def hexToColor(hex):
    return int(hex.replace('#', ''), 16)

class ColorVal:
    NONE = Color(0,0,0)
    BLUE = Color(0,31,255)
    CYAN = Color(0,255,255)
    DARK_ORANGE = Color(255,63,0)
    DARK_YELLOW = Color(250,210,0)
    GREEN = Color(0,255,0)
    LIGHT_GREEN = Color(127,255,0)
    ORANGE = Color(255,128,0)
    MINT = Color(63,255,63)
    PINK = Color(255,0,127)
    PURPLE = Color(127,0,255)
    RED = Color(255,0,0)
    SKY = Color(0,191,255)
    WHITE = Color(255,255,255)
    YELLOW = Color(255,255,0)

class ColorPattern:
    SOLID = None
    ''' [# ON, # OFF] '''
    ALTERNATING = [1, 1]
    ONE_OF_THREE = [1, 2]
    TWO_OUT_OF_THREE = [2, 1]
    MOD_SEVEN = [1, 6]
    FOUR_ON_FOUR_OFF = [4, 4]

class LEDEvent:
    NOCONTROL = 'noControlDisplay'

    configurable_events = [
        {
            "event": Evt.RACE_STAGE,
            "label": "Race Staging"
        },
        {
            "event": Evt.RACE_START,
            "label": "Race Start"
        },
        {
            "event": Evt.RACE_FINISH,
            "label": "Race Finish"
        },
        {
            "event": Evt.RACE_STOP,
            "label": "Race Stop"
        },
        {
            "event": Evt.LAPS_CLEAR,
            "label": "Save/Clear Laps"
        },
        {
            "event": Evt.CROSSING_ENTER,
            "label": "Gate Entrance"
        },
        {
            "event": Evt.CROSSING_EXIT,
            "label": "Gate Exit"
        },
        {
            "event": Evt.STARTUP,
            "label": "Server Startup"
        },
        {
            "event": Evt.SHUTDOWN,
            "label": "Server Shutdown"
        }
    ]

class LEDEffect(UserDict):
    def __init__(self, name, label, handlerFn, validEvents, defaultArgs=None):
        UserDict.__init__(self, {
            "name": name,
            "label": label,
            "handlerFn": handlerFn,
            "validEvents": validEvents,
            "defaultArgs": defaultArgs
        })
