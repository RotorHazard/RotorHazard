'''
RotorHazard event manager
'''

import logging
import gevent.event
import copy
from monotonic import monotonic

logger = logging.getLogger(__name__)

class EventManager:
    processEventObj = gevent.event.Event()

    events = {}
    eventOrder = {}
    eventThreads = {}

    def __init__(self):
        pass

    def on(self, event, name, handlerFn, defaultArgs=None, priority=200, unique=False):
        if defaultArgs == None:
            defaultArgs = {}

        if event not in self.events:
            self.events[event] = {}

        self.events[event][name] = {
            "handlerFn": handlerFn,
            "defaultArgs": defaultArgs,
            "priority": priority,
            "unique": unique
        }

        self.eventOrder[event] = [key for key, _value in sorted(self.events[event].items(), key=lambda x: x[1]['priority'])]

        return True

    def off(self, event, name):
        if event not in self.events:
            return True

        if name not in self.events[event]:
            return True

        del(self.events[event][name])

        self.eventOrder[event] = [key for key, _value in sorted(self.events[event].items(), key=lambda x: x[1]['priority'])]

        return True

    def trigger(self, event, evtArgs=None):
        # logger.debug('-Triggered event- {0}'.format(event))
        evt_list = []
        if event in self.eventOrder:
            for name in self.eventOrder[event]:
                evt_list.append([event, name])
        if Evt.ALL in self.eventOrder:
            for name in self.eventOrder[Evt.ALL]:
                evt_list.append([Evt.ALL, name])

        if len(evt_list):
            for ev, name in evt_list:
                handler = self.events[ev][name]
                args = copy.copy(handler['defaultArgs'])

                if evtArgs:
                    if args:
                        args.update(evtArgs)
                    else:
                        args = evtArgs

                if ev == Evt.ALL:
                    args['_eventName'] = event

                if handler['unique']:
                    threadName = name + str(monotonic())
                else:
                    threadName = name

                # stop any threads with same name
                for token in self.eventThreads.copy():
                    if token in self.eventThreads and self.eventThreads[token]['name'] == name:
                        self.eventThreads[token]['thread'].kill(block=False)
                    if token in self.eventThreads and self.eventThreads[token]['thread'].dead:
                        self.eventThreads.pop(token, False)

                if handler['priority'] < 100:
                    handler['handlerFn'](args)
                else:
                    greenlet = gevent.spawn(handler['handlerFn'], args)
                    self.eventThreads[greenlet.minimal_ident] = {
                        'name': threadName,
                        'thread': greenlet
                        }

class Evt:
    # Special
    ALL = 'all'
    # Program
    STARTUP = 'startup'
    SHUTDOWN = 'shutdown'
    OPTION_SET = 'optionSet'
    MESSAGE_STANDARD = 'messageStandard'
    MESSAGE_INTERRUPT = 'messageInterrupt'
    # Event setup
    FREQUENCY_SET = 'frequencySet'
    ENTER_AT_LEVEL_SET = 'enterAtLevelSet'
    EXIT_AT_LEVEL_SET = 'exitAtLevelSet'
    PROFILE_SET = 'profileSet'
    PROFILE_ADD = 'profileAdd'
    PROFILE_ALTER = 'profileAlter'
    PROFILE_DELETE = 'profileDelete'
    PILOT_ADD = 'pilotAdd'
    PILOT_ALTER = 'pilotAlter'
    PILOT_DELETE = 'pilotDelete'
    HEAT_SET = 'heatSet'
    HEAT_ADD = 'heatAdd'
    HEAT_DUPLICATE = 'heatDuplicate'
    HEAT_ALTER = 'heatAlter'
    HEAT_DELETE = 'heatDelete'
    HEAT_GENERATE = 'heatGenerate'
    CLASS_ADD = 'classAdd'
    CLASS_DUPLICATE = 'classDuplicate'
    CLASS_ALTER = 'classAlter'
    CLASS_DELETE = 'classDelete'
    # Database
    DATABASE_BACKUP = 'databaseBackup'
    DATABASE_RESET = 'databaseReset'
    DATABASE_INITIALIZE = 'databaseInitialize'
    DATABASE_RECOVER = 'databaseRecover'
    DATABASE_RESTORE = 'databaseRestore'
    DATABASE_DELETE_BACKUP = 'databaseDeleteBackup'
    DATABASE_EXPORT = 'databaseExport'
    # Race setup
    MIN_LAP_TIME_SET = 'minLapTimeSet'
    MIN_LAP_BEHAVIOR_SET = 'minLapBehaviorSet'
    RACE_ALTER = 'raceAlter'
    RACE_FORMAT_SET = 'raceFormatSet'
    RACE_FORMAT_ADD = 'raceFormatAdd'
    RACE_FORMAT_ALTER = 'raceFormatAlter'
    RACE_FORMAT_DELETE = 'raceFormatDelete'
    # Race sequence
    RACE_SCHEDULE = 'raceSchedule'
    RACE_SCHEDULE_CANCEL = 'raceScheduleCancel'
    RACE_STAGE = 'raceStage'
    RACE_START_COUNTDOWN = 'raceStartCountdown'
    RACE_START = 'raceStart'
    RACE_TICK = 'raceTick'
    RACE_FINISH = 'raceFinish'
    RACE_STOP = 'raceStop'
    RACE_WIN = 'raceWin'
    RACE_FIRST_PASS = 'raceFirstPass'
    RACE_LAP_RECORDED = 'raceLapRecorded'
    RACE_SPLIT_RECORDED = 'raceSplitRecorded'
    CROSSING_ENTER = 'crossingEnter'
    CROSSING_EXIT = 'crossingExit'
    # Race management
    LAPS_SAVE = 'lapsSave'
    LAPS_DISCARD = 'lapsDiscard'
    LAPS_CLEAR = 'lapsClear'
    LAPS_RESAVE = 'lapsResave'
    LAP_DELETE = 'lapDelete'
    LAP_RESTORE_DELETED = 'lapRestoreDeleted'
    # Results cache
    CACHE_CLEAR = 'cacheClear'
    CACHE_READY = 'cacheReady'
    CACHE_FAIL = 'cacheFail'
    # CLUSTER
    CLUSTER_JOIN = 'clusterJoin'
    # LED
    LED_EFFECT_SET = 'LedEffectSet'
    LED_BRIGHTNESS_SET = 'LedBrightnessSet'
    LED_MANUAL = 'LedManual'
    LED_SET_MANUAL = 'LedSetManual'
    # VRX Controller
    VRX_DATA_RECEIVE = 'VrxDataRecieve'

    SENSOR_UPDATE = 'sensorUpdate'

