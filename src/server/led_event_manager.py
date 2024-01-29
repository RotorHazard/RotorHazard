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
            if event in [Evt.SHUTDOWN]:
                priority = 50 # event is direct (blocking)
            else:
                priority = 150 # event is normal (threaded/non-blocking)

            self.Events.on(event, 'LED', self.activateEffect, args, priority)
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

    # Stops any currently-running effect and runs the given effect
    def runNewEffect(self, new_effect, args):
        result = False
        if hasattr(new_effect, 'run_effect'):
            cur_effect = self.running_effect
            self.running_effect = None
            if hasattr(cur_effect, 'stop_effect'):
                cur_effect.stop_effect()  # terminate greenlet thread and wait for it to finish
                if self.running_effect:  # if another effect got started while waiting for 'join' then
                    return False         #  abort this effect
            result = new_effect.run_effect(args)
            self.running_effect = new_effect
        return result

    # Activates the given effect
    @catchLogExceptionsWrapper
    def activateEffect(self, args):
        if args.get('_eventName') == Evt.SHUTDOWN:
            self.clear()
            return False
        new_effect = args.get('effect')
        result = self.runNewEffect(new_effect, args)
        if result == False:
            logger.debug('LED effect %s produced no output', args.get('handler_fn'))
        if not args.get('preventIdle', False):
            time_val = args.get('time')
            if not time_val:  # if zero or none then default to 1 second delay
                time_val = 1
            gevent.spawn_later(float(time_val), self.activateIdle, new_effect)
        return True

    # Activates the idle effect (if configured)
    @catchLogExceptionsWrapper
    def activateIdle(self, last_effect):
        # if no current effect or effect has not changed during idle delay time
        if (not self.running_effect) or (last_effect and last_effect == self.running_effect):
            event = None
            if self._racecontext.race.race_status == RHRace.RaceStatus.DONE:
                event = LEDEvent.IDLE_DONE
            elif self._racecontext.race.race_status == RHRace.RaceStatus.READY:
                event = LEDEvent.IDLE_READY
            elif self._racecontext.race.race_status == RHRace.RaceStatus.RACING:
                event = LEDEvent.IDLE_RACING
            if event and event in self.events:
                idle_effect = self.eventEffects[self.events[event]]
                self.runNewEffect(idle_effect, self.idleArgs[event])


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
        self.terminate_flag = False

    def run_effect(self, args):
        self.terminate_flag = False
        self.fn_thread = gevent.spawn(self.handler_fn, {**args, '_effect':self})

    def stop_effect(self, wait_flag=True):
        self.terminate_flag = True
        if wait_flag and hasattr(self.fn_thread, 'join'):
            self.fn_thread.join(10)  # wait for thread to finish (up to timeout value)

    def is_terminated(self):
        return self.terminate_flag
