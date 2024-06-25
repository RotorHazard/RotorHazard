'''
RotorHazard filter manager
'''

import logging
from RHUtils import catchLogExceptionsWrapper

logger = logging.getLogger(__name__)

class FilterManager:
    def __init__(self, rhapi):
        self.filters = {}
        self.filterOrder = {}
        self._rhapi = rhapi

    def add_filter(self, filter_type, name, filter_fn, priority=200):
        if filter_type not in self.filters:
            self.filters[filter_type] = {}

        self.filters[filter_type][name] = {
            "filter_fn": filter_fn,
            "priority": priority,
        }

        self.filterOrder[filter_type] = [key for key, _value in sorted(self.filters[filter_type].items(), key=lambda x: x[1]['priority'])]

        return True

    def remove_filter(self, filter_type, name):
        if filter_type not in self.filters:
            return True

        if name not in self.filters[filter_type]:
            return True

        del(self.filters[filter_type][name])

        self.filterOrder[filter_type] = [key for key, _value in sorted(self.filters[filter_type].items(), key=lambda x: x[1]['priority'])]

        return True

    def run_filters(self, filter_type, data):
        filter_list = []
        if filter_type in self.filterOrder:
            for name in self.filterOrder[filter_type]:
                filter_list.append(name)

        if len(filter_list):
            for name in filter_list:
                filter = self.filters[filter_type][name]
                data = self.run_filter(filter['filter_fn'], data)

        return data

    @catchLogExceptionsWrapper
    def run_filter(self, handler, data):
        return handler(data)


class Flt:
    BEFORE_ALL = 'before_event_all'
    AFTER_ALL = 'after_event_all'

    # Special
    ALL = 'all'
    UI_DISPATCH = 'dispatch'
    # Program
    STARTUP = 'startup'
    SHUTDOWN = 'shutdown'
    OPTION_SET = 'optionSet'
    CONFIG_SET = 'configSet'
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
    RACE_PILOT_DONE = 'racePilotDone'
    CROSSING_ENTER = 'crossingEnter'
    CROSSING_EXIT = 'crossingExit'
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

