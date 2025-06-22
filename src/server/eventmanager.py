'''
RotorHazard event manager
'''

import logging
import gevent
import copy
from RHUtils import catchLogExceptionsWrapper
from time import monotonic

logger = logging.getLogger(__name__)

class EventManager:
    processEventObj = gevent.event.Event()

    events = {}
    eventOrder = {}
    eventThreads = {}

    def __init__(self, racecontext):
        self._racecontext = racecontext

    def on(self, event, name, handler_fn, default_args=None, priority=200, unique=False):
        if self._racecontext.serverconfig.get_item('LOGGING', 'EVENTS') >= 1:
            logger.debug("eventmanager.on, event={}, name='{}', priority={}, unique={}, default_args: {}".\
                     format(event, name, priority, unique, str(default_args)[:80]))
        if default_args == None:
            default_args = {}

        if event not in self.events:
            self.events[event] = {}

        self.events[event][name] = {
            "handler_fn": handler_fn,
            "default_args": default_args,
            "priority": priority,
            "unique": unique
        }

        self.eventOrder[event] = [key for key, _value in sorted(self.events[event].items(), key=lambda x: x[1]['priority'])]

        return True

    def off(self, event, name):
        if self._racecontext.serverconfig.get_item('LOGGING', 'EVENTS') >= 1:
            logger.debug("eventmanager.off, event={}, name='{}'".format(event, name))
        if event not in self.events:
            return True

        if name not in self.events[event]:
            return True

        del(self.events[event][name])

        self.eventOrder[event] = [key for key, _value in sorted(self.events[event].items(), key=lambda x: x[1]['priority'])]

        return True

    def trigger(self, event, evt_args=None):
        if logger.getEffectiveLevel() <= logging.DEBUG and \
            self._racecontext.serverconfig.get_item('LOGGING', 'EVENTS') >= 2:  # if DEBUG msgs actually being logged
            logger.debug("eventmanager.trigger, event={}, evt_args: {}".format(event, str(evt_args)[:80]))
        evt_list = []
        if event in self.eventOrder:
            for name in self.eventOrder[event]:
                evt_list.append([event, name])
        if event != Evt.HEARTBEAT and Evt.ALL in self.eventOrder:
            for name in self.eventOrder[Evt.ALL]:
                evt_list.append([Evt.ALL, name])

        if len(evt_list):
            for ev, name in evt_list:
                handler = self.events[ev][name]
                args = copy.copy(handler['default_args'])

                if evt_args:
                    if args:
                        args.update(evt_args)
                    else:
                        args = evt_args

                args['_eventName'] = event

                if handler['unique']:
                    threadName = name + str(monotonic())
                else:
                    threadName = name

                if logger.getEffectiveLevel() <= logging.DEBUG and \
                    self._racecontext.serverconfig.get_item('LOGGING', 'EVENTS') >= 2:  # if DEBUG msgs actually being logged
                    logger.debug("eventmanager.trigger calling handler for event={}, name='{}', priority={}".\
                                 format(event, name, handler['priority']))

                if handler['priority'] < 100:
                    self.run_handler(handler['handler_fn'], args)
                else:
                    gevent.spawn(self.run_handler, handler['handler_fn'], args)

    @catchLogExceptionsWrapper
    def run_handler(self, handler, args):
        return handler(args)


class Evt:
    # Special
    ALL = 'all'
    HEARTBEAT = 'heartbeat'
    UI_DISPATCH = 'dispatch'
    # Program
    STARTUP = 'startup'
    SHUTDOWN = 'shutdown'
    OPTION_SET = 'optionSet'
    CONFIG_SET = 'configSet'
    MESSAGE_STANDARD = 'messageStandard'
    MESSAGE_INTERRUPT = 'messageInterrupt'
    RESTART_REQUIRED = 'restartRequired'
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
    DATABASE_IMPORT = 'databaseImport'
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
    RACE_START = 'raceStart'
    RACE_FINISH = 'raceFinish'
    RACE_STOP = 'raceStop'
    RACE_WIN = 'raceWin'
    RACE_FIRST_PASS = 'raceFirstPass'
    RACE_LAP_RECORDED = 'raceLapRecorded'
    RACE_PILOT_LEADING = 'racePilotLeading'
    RACE_PILOT_DONE = 'racePilotDone'
    CROSSING_ENTER = 'crossingEnter'
    CROSSING_EXIT = 'crossingExit'
    RACE_INITIAL_PASS = 'raceInitialPass'
    # Race management
    LAPS_SAVE = 'lapsSave'
    LAPS_DISCARD = 'lapsDiscard'
    LAPS_CLEAR = 'lapsClear'
    LAPS_RESAVE = 'lapsResave'
    LAP_DELETE = 'lapDelete'
    LAP_RESTORE_DELETED = 'lapRestoreDeleted'
    ROUNDS_COMPLETE = 'roundsComplete'
    # Results cache
    CACHE_CLEAR = 'cacheClear'
    CACHE_READY = 'cacheReady'
    CACHE_FAIL = 'cacheFail'
    # CLUSTER
    CLUSTER_JOIN = 'clusterJoin'
    # LED
    LED_INITIALIZE = 'LED_Initialize'
    LED_EFFECT_SET = 'LedEffectSet'
    LED_BRIGHTNESS_SET = 'LedBrightnessSet'
    LED_MANUAL = 'LedManual'
    LED_SET_MANUAL = 'LedSetManual'
    # VRX Controller
    VRX_INITIALIZE = 'VRxC_Initialize'
    VRX_DATA_RECEIVE = 'VrxDataRecieve'
    # Initializations
    POINTS_INITIALIZE = 'RacePoints_Initialize'
    CLASS_RANK_INITIALIZE = 'RaceClassRanking_Initialize'
    HEAT_GENERATOR_INITIALIZE = 'HeatGenerator_Initialize'
    ACTIONS_INITIALIZE = 'actionsInitialize'
    DATA_IMPORT_INITIALIZE = 'Import_Initialize'
    DATA_EXPORT_INITIALIZE = 'Export_Initialize'

