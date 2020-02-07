'''
LED event manager
Wires events to handlers
'''

import gevent

class LEDEventManager:
    processEventObj = gevent.event.Event()

    events = {}
    eventHandlers = {}
    eventThread = None

    def __init__(self, strip, config):
        self.strip = strip
        self.config = config

    def isEnabled(self):
        return True

    def registerEffect(self, name, label, handlerFn, validEvents, defaultArgs=None):
        self.eventHandlers[name] = {
            "label": label,
            "handlerFn": handlerFn,
            "validEvents": validEvents,
            "defaultArgs": defaultArgs
        }
        return True

    def getRegisteredHandlers(self):
        return self.eventHandlers

    def getEventHandler(self, event):
        if event in self.events:
            return self.events[event]
        else:
            return False

    def setEventHandler(self, event, name):
        self.events[event] = name
        return True

    def event(self, event, eventArgs=None):
        if event in self.events:
            currentEvent = self.events[event]
            if currentEvent in self.eventHandlers:
                handler = self.eventHandlers[currentEvent]
                args = handler['defaultArgs']
                if eventArgs:
                    if args:
                        args.update(eventArgs)
                    else:
                        args = eventArgs

                # restart thread regardless of status
                if self.eventThread is not None:
                    self.eventThread.kill()

                self.eventThread = gevent.spawn(handler['handlerFn'], self.strip, self.config, args)
                return True

        return False

    def eventDirect(self, event, eventArgs=None):
        """ Do event call using calling thread """
        if event in self.events:
            currentEvent = self.events[event]
            if currentEvent in self.eventHandlers:
                handler = self.eventHandlers[currentEvent]
                args = handler['defaultArgs']
                if eventArgs:
                    if args:
                        args.update(eventArgs)
                    else:
                        args = eventArgs

                # stop any current thread
                if self.eventThread is not None:
                    self.eventThread.kill()
                    self.eventThread = None

                handler['handlerFn'](self.strip, self.config, args)
                return True

        return False

    def clear(self):
        self.eventHandlers['clear']['handlerFn'](self.strip, self.config)

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
    SOLID = 0
    ALTERNATING = 1
    TWO_OUT_OF_THREE = 2
    MOD_SEVEN = 3
    FOUR_ON_FOUR_OFF = 4

class LEDEvent:
    NOCONTROL = 'noControlDisplay'
    MANUAL = 'manual'
    RACESTAGE = 'raceStage'
    RACESTART = 'raceStart'
    RACEFINISH = 'raceFinish'
    RACESTOP = 'raceStop'
    RACEWIN = 'raceWin'
    CROSSINGENTER = 'crossingEnter'
    CROSSINGEXIT = 'crossingExit'
    STARTUP = 'startup'
    SHUTDOWN = 'shutdown'

    configurable_events = [
        {
            "event": RACESTAGE,
            "label": "Race Staging"
        },
        {
            "event": RACESTART,
            "label": "Race Start"
        },
        {
            "event": RACEFINISH,
            "label": "Race Finish"
        },
        {
            "event": RACESTOP,
            "label": "Race Stop"
        },
        {
            "event": CROSSINGENTER,
            "label": "Gate Entrance"
        },
        {
            "event": CROSSINGEXIT,
            "label": "Gate Exit"
        },
        {
            "event": STARTUP,
            "label": "Server Startup"
        },
        {
            "event": SHUTDOWN,
            "label": "Server Shutdown"
        }
    ]
