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
    PILOT_ADD = 'pilotAdd'
    PILOT_ALTER = 'pilotAlter'
    HEAT_ADD = 'heatAdd'
    HEAT_DUPLICATE = 'heatDuplicate'
    HEAT_ALTER = 'heatAlter'
    CLASS_ADD = 'classAdd'
    CLASS_DUPLICATE = 'classDuplicate'
    CLASS_ALTER = 'classAlter'
    PROFILE_ADD = 'profileAdd'
    PROFILE_DUPLICATE = 'profileDuplicate' ## ***
    PROFILE_ALTER = 'profileAlter'
    RACE_FORMAT_ADD = 'raceFormatAdd'
    RACE_FORMAT_DUPLICATE = 'raceFormatDuplicate' ## ***
    RACE_FORMAT_ALTER = 'raceFormatAlter'
    OPTION_GET = 'optionGet'
    OPTION_GET_INT = 'optionGetInt'
    OPTION_SET = 'optionSet'

    RACE_STAGE = 'raceStage'
    LAPS_SAVE = 'lapsSave'
    RACE_RESULTS = 'raceResults'
    RACE_TEAM_RESULTS = 'raceTeamResults'
    RACE_COOP_RESULTS = 'raceCoopResults'
    RACE_SET_HEAT = 'raceSetHeat'

    EMIT_UI = 'emitUI'
    EMIT_PLUGIN_LIST = 'emitPluginList'
    EMIT_HEAT_PLAN = 'emitHeatPlan'
    EMIT_SENSOR_DATA = 'emitSensorData'
    EMIT_RACE_LIST = 'emitRaceList'
    EMIT_HEAT_LIST = 'emitHeatList'
    EMIT_HEAT_DATA = 'emitHeatData'
    EMIT_RECENT_HEAT_DATA = 'emitRecentHeatData'
    EMIT_HEAT_EXPANDED = 'emitHeatExpanded'
    EMIT_CLASS_LIST = 'emitClassList'
    EMIT_CLASS_DATA = 'emitClassData'
    EMIT_FORMAT_DATA = 'emitFormatData'
    EMIT_PILOT_LIST = 'emitPilotList'
    EMIT_PILOT_DATA = 'emitPilotData'
    EMIT_SEAT_DATA = 'emitSeatData'
    EMIT_PHONETIC_DATA = 'emitPhoneticData'
    EMIT_PHONETIC_LEADER = 'emitPhoneticLeader'
    EMIT_PHONETIC_TEXT = 'emitPhoneticText'
    EMIT_PHONETIC_SPLIT = 'emitPhoneticSplit'

    LEADERBOARD_BUILD_RACE = 'leaderboardBuildRace'
    LEADERBOARD_BUILD_HEAT = 'leaderboardBuildHeat'
    LEADERBOARD_BUILD_CLASS = 'leaderboardBuildClass'
    LEADERBOARD_BUILD_EVENT = 'leaderboardBuildEvent'
    LEADERBOARD_BUILD_INCREMENTAL = 'leaderboardBuildIncremental'
    LEADERBOARD_SORT_AND_RANK = 'leaderboardSortAndRank'
    GAP_INFO = 'gapInfo'

    CALIBRATION_FALLBACK = 'calibrationFallback'
