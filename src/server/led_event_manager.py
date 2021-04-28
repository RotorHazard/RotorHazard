'''
LED event manager
Wires events to handlers

{
    'manual': False,
    'include': [],
    'exclude': [Evt.ALL]
}

'''

import copy
import json
from . import RHRace
import gevent
from .Results import CacheStatus
from .eventmanager import Evt
from six.moves import UserDict

class LEDEventManager:
    events = {}
    idleArgs = {}
    eventEffects = {}
    eventThread = None

    def __init__(self, eventmanager, strip, RHData, RACE, Language):
        self.Events = eventmanager
        self.strip = strip
        self.RHData = RHData
        self.RACE = RACE
        self.Language = Language

        # hold
        self.registerEffect(LEDEffect("hold", "Hold", lambda *args: None, {
                'include': [Evt.SHUTDOWN, LEDEvent.IDLE_DONE, LEDEvent.IDLE_READY, LEDEvent.IDLE_RACING],
                'exclude': [Evt.STARTUP],
                'recommended': [Evt.ALL]
            }, {
                'preventIdle': True
            }))

        # do nothing
        self.registerEffect(LEDEffect("none", "No Effect", lambda *args: None, {
                'manual': False,
                'exclude': [Evt.STARTUP],
                'recommended': [Evt.ALL]
            }))

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

        if name not in self.eventEffects:
            return None

        if name == 'none':
            self.Events.off(event, 'LED')
            return True

        args = copy.deepcopy(self.eventEffects[name]['defaultArgs'])
        if args is None:
            args = {}

        args.update({
            'handlerFn': self.eventEffects[name]['handlerFn'],
            'strip': self.strip,
            'RHData': self.RHData,
            'RACE': self.RACE,
            'Language': self.Language,
            'manager': self,
            })

        if event in [LEDEvent.IDLE_READY, LEDEvent.IDLE_DONE, LEDEvent.IDLE_RACING]:
            # event is idle
            self.idleArgs[event] = args
        else:
            if event in [Evt.SHUTDOWN]:
                priority = 50 # event is direct (blocking)
            else:
                priority = 150 # event is normal (threaded/non-blocking)

                self.Events.on(event, 'LED', self.activateEffect, args, priority)
        return True

    def clear(self):
        self.setEventEffect(Evt.LED_MANUAL, 'clear')
        self.Events.trigger(Evt.LED_MANUAL, {'time': None, 'preventIdle': True})

    def getDisplayColor(self, node_index, from_result=False):
        mode = self.RHData.get_optionInt('ledColorMode', 0)
        color = False

        if mode == 1: # by pilot
            color = '#ffffff'
            if from_result:
                if self.RACE.last_race_results and self.RACE.last_race_cacheStatus == CacheStatus.VALID and 'by_race_time' in self.RACE.last_race_results:
                    for line in self.RACE.last_race_results['by_race_time']:
                        if line['node'] == node_index:
                            color = self.RHData.get_pilot(line['pilot_id']).color
                            break
                elif self.RACE.results and 'by_race_time' in self.RACE.results:
                    for line in self.RACE.results['by_race_time']:
                        if line['node'] == node_index:
                            color = self.RHData.get_pilot(line['pilot_id']).color
                            break
            else:
                if self.RACE.current_heat:
                    for heatNode in self.RHData.get_heatNodes_by_heat(self.RACE.current_heat):
                        if heatNode.node_index == node_index:
                            if heatNode.pilot_id:
                                color = self.RHData.get_pilot(heatNode.pilot_id).color
                            break
        elif mode == 2: # by frequency

            profile = self.RHData.get_profile(self.RHData.get_optionInt('currentProfile'))
            profile_freqs = json.loads(profile.frequencies)
            freq = profile_freqs["f"][node_index]

            colorFreqSerial = self.RHData.get_option('ledColorFreqs', False)
            if colorFreqSerial:
                colorFreqs = json.loads(colorFreqSerial)
                color = colorFreqs[node_index]
            else:
                if freq <= 5672:
                    color = '#ffffff' # White
                elif freq <= 5711:
                    color = '#ff0000' # Red
                elif freq <= 5750:
                    color = '#ff8000' # Orange
                elif freq <= 5789:
                    color = '#ffff00' # Yellow
                elif freq <= 5829:
                    color = '#00ff00' # Green
                elif freq <= 5867:
                    color = '#0000ff' # Blue
                elif freq <= 5906:
                    color = '#8000ff' # Dark Violet
                else:
                    color = '#ff0080' # Deep Pink

        else: # by node
            colorNodeSerial = self.RHData.get_option('ledColorNodes', False)
            if colorNodeSerial:
                colorNodes = json.loads(colorNodeSerial)
            else:
                colorNodes = [
                    "#001fff", # Blue
                    "#ff3f00", # Orange
                    "#7fff00", # Lime green
                    "#ffff00", # Yellow
                    "#7f00ff", # Magenta
                    "#ff007f", # Purple
                    "#3fff3f", # Mint
                    "#00bfff", # Cyan
                ]

            if node_index + 1 < len(colorNodes):
                color = colorNodes[node_index]

        if not color:
            color = '#ffffff'

        return hexToColor(color)

    def activateEffect(self, args):
        args['handlerFn'](args)
        if 'preventIdle' not in args or not args['preventIdle']:
            if 'time' in args:
                time = args['time']
            else:
                time = 0

            if time:
                gevent.sleep(float(time))

            self.activateIdle(args)

    def activateIdle(self, args):
        gevent.idle()
        event = None
        if self.RACE.race_status == RHRace.RaceStatus.DONE:
            event = LEDEvent.IDLE_DONE
        elif self.RACE.race_status == RHRace.RaceStatus.READY:
            event = LEDEvent.IDLE_READY
        elif self.RACE.race_status == RHRace.RaceStatus.RACING:
            event = LEDEvent.IDLE_RACING

        if event and event in self.events:
            self.eventEffects[self.events[event]]['handlerFn'](self.idleArgs[event])


class NoLEDManager():
    def __init__(self):
        pass

    def isEnabled(self):
        return False

    def __getattr__(self, *args, **kwargs):
        def nothing(*args, **kwargs):
            return False
        return nothing

# Similar to NoLEDManager but with enough support to send 'effect' events to cluster timers
class ClusterLEDManager():
    eventEffects = {}

    def __init__(self):
        pass

    def isEnabled(self):
        return False

    def registerEffect(self, effect):
        self.eventEffects[effect['name']] = effect
        return True

    def getRegisteredEffects(self):
        return self.eventEffects

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

def hexToColor(hexColor):
    return int(hexColor.replace('#', ''), 16)

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
    IDLE_READY = 'ledIdleReady'
    IDLE_DONE = 'ledIdleDone'
    IDLE_RACING = 'ledIdleRacing'

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
            "event": Evt.RACE_LAP_RECORDED,
            "label": "Lap Recorded"
        },
        {
            "event": Evt.RACE_WIN,
            "label": "Race Winner Declared"
        },
        {
            "event": Evt.MESSAGE_STANDARD,
            "label": "Message (Normal)"
        },
        {
            "event": Evt.MESSAGE_INTERRUPT,
            "label": "Message (Priority)"
        },
        {
            "event": Evt.STARTUP,
            "label": "Server Startup"
        },
        {
            "event": Evt.SHUTDOWN,
            "label": "Server Shutdown"
        },
        {
            "event": IDLE_READY,
            "label": "Idle: System Ready"
        },
        {
            "event": IDLE_RACING,
            "label": "Idle: Racing"
        },
        {
            "event": IDLE_DONE,
            "label": "Idle: Race Stopped"
        },
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
