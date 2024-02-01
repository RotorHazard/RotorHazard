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
import RHRace
import RHUtils
from RHUtils import catchLogExceptionsWrapper, cleanVarName
import gevent
from eventmanager import Evt
from collections import UserDict
import logging

logger = logging.getLogger(__name__)

class LEDEventManager:
    events = {}
    idleArgs = {}
    eventEffects = {}
    displayColorCache = []
    running_effect = None

    def __init__(self, eventmanager, strip, RaceContext, RHAPI):
        self.Events = eventmanager
        self.strip = strip
        self._racecontext = RaceContext
        self._rhapi = RHAPI

        # hold
        self.registerEffect(LEDEffect("Hold", lambda *_args: None, {
                'include': [Evt.SHUTDOWN, LEDEvent.IDLE_DONE, LEDEvent.IDLE_READY, LEDEvent.IDLE_RACING],
                'exclude': [Evt.STARTUP],
                'recommended': [Evt.ALL]
            }, {
                'preventIdle': True
            },
            name="hold",
            ))

        # do nothing
        self.registerEffect(LEDEffect("No Effect", lambda *_args: None, {
                'manual': False,
                'exclude': [Evt.STARTUP],
                'recommended': [Evt.ALL]
            },
            name="none",
            ))

        self.Events.trigger(Evt.LED_INITIALIZE, {
            'register_fn': self.registerEffect
            })

    def isEnabled(self):
        return True

    def registerEffect(self, effect):
        self.eventEffects[effect.name] = effect
        return True

    def getRegisteredEffects(self):
        return self.eventEffects

    def getEventEffect(self, event):
        if event in self.events:
            return self.events[event]

    def setEventEffect(self, event, name):
        self.events[event] = name

        if name not in self.eventEffects:
            return False

        if name == 'none':
            self.Events.off(event, 'LED')
            return True

        args = copy.deepcopy(self.eventEffects[name].default_args)
        if args is None:
            args = {}

        args.update({
            'effect': self.eventEffects[name],
            'strip': self.strip,
            'manager': self,
            'RHAPI': self._rhapi
            })

        if event in [LEDEvent.IDLE_READY, LEDEvent.IDLE_DONE, LEDEvent.IDLE_RACING]:
            # event is idle
            self.idleArgs[event] = args
        else:
            self.Events.on(event, 'LED', self.activateEffect, args, 150)
        return True

    def clear(self):
        self.setEventEffect(Evt.LED_MANUAL, 'clear')
        self.Events.trigger(Evt.LED_MANUAL, {'time': None, 'preventIdle': True})

    def getDisplayColor(self, seat_index, from_result=False):
        if seat_index is None:
            return RHUtils.hexToColor('#000000')

        if from_result and self._racecontext.rhdata.get_optionInt('ledColorMode', 0) == 1:
            last_results = self._racecontext.last_race.get_results()
            results = self._racecontext.race.get_results()

            if last_results and 'by_race_time' in last_results:
                for line in last_results['by_race_time']:
                    if line['node'] == seat_index:
                        return RHUtils.hexToColor(self._racecontext.rhdata.get_pilot(line['pilot_id']).color)
            elif results and 'by_race_time' in results:
                for line in results['by_race_time']:
                    if line['node'] == seat_index:
                        return RHUtils.hexToColor(self._racecontext.rhdata.get_pilot(line['pilot_id']).color)

        seat_colors = self._racecontext.race.seat_colors 
        if seat_index < len(seat_colors):
            return seat_colors[seat_index]

        return RHUtils.hexToColor('#ffffff')

    # Activates the given effect
    @catchLogExceptionsWrapper
    def activateEffect(self, args):
        if args.get('_eventName') == Evt.SHUTDOWN:
            self.clear()
            return False
        new_effect = copy.copy(args.get('effect'))

        if self.running_effect:
            self.running_effect.stop_effect()

        new_effect.run_effect(args, self.get_idle_fn)
        self.running_effect = new_effect

    # Provides linkage to the idle effect (if configured)
    @catchLogExceptionsWrapper
    def get_idle_fn(self):
        if self._racecontext.race.race_status == RHRace.RaceStatus.DONE:
            event = LEDEvent.IDLE_DONE
        elif self._racecontext.race.race_status == RHRace.RaceStatus.READY:
            event = LEDEvent.IDLE_READY
        elif self._racecontext.race.race_status == RHRace.RaceStatus.RACING:
            event = LEDEvent.IDLE_RACING

        if event and event in self.events:
            return (self.eventEffects[self.events[event]].handler_fn, self.idleArgs[event])


class NoLEDManager():
    def __init__(self):
        pass

    def isEnabled(self):
        return False

    def __getattr__(self, *_args, **_kwargs):
        def nothing(*_args, **_kwargs):
            return False
        return nothing

# Similar to NoLEDManager but with enough support to send 'effect' events to cluster timers
class ClusterLEDManager():
    eventEffects = {}

    def __init__(self, Events):
        Events.trigger('LED_Initialize', {
            'register_fn': self.registerEffect
            })

    def isEnabled(self):
        return False

    def registerEffect(self, effect):
        self.eventEffects[effect['name']] = effect
        return True

    def getRegisteredEffects(self):
        return self.eventEffects

    def __getattr__(self, *_args, **_kwargs):
        def nothing(*_args, **_kwargs):
            return False
        return nothing

# Generic data structures for working with LED commands

def Color(red, green, blue):
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return (red << 16) | (green << 8) | blue

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
            "event": Evt.CLUSTER_JOIN,
            "label": "Joined Timer Cluster"
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

class LEDEffectExit(BaseException):
    pass

def effect_delay(ms, args):
    effect_obj = args.get('_effect')
    if not hasattr(effect_obj, 'terminate') or effect_obj.terminate:
        raise LEDEffectExit
    if ms:
        gevent.sleep(ms/1000.0)
        if effect_obj.terminate:
            raise LEDEffectExit

class LEDEffect():
    def __init__(self, label, handler_fn, valid_events, default_args=None, name=None):
        if name is None:
            name = cleanVarName(label)

        self.label = label
        self.handler_fn = handler_fn
        self.valid_events = valid_events
        self.default_args = default_args
        self.name = name
        self.fn_thread = None
        self.terminate = False
        self.idler = None

    def effect_runner(self, args):
        try:
            # run base effect
            self.handler_fn(args)

            # optional delay
            time_val = args.get('time') or 0
            gevent.sleep(time_val)

            # run idler
            if not self.terminate and not args.get('preventIdle'):
                idler_fn, idler_args = self.idler()
                idler_fn({**idler_args, '_effect':self})
        except LEDEffectExit:
            pass

    def run_effect(self, args, idler):
        self.idler = idler
        self.terminate = False
        self.fn_thread = gevent.spawn(self.effect_runner, {**args, '_effect':self})

    def stop_effect(self):
        self.terminate = True
        self.fn_thread.join(0.01) # wait to close effect if brief
