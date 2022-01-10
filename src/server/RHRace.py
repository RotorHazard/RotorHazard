'''Class to hold race management variables.'''

from enum import IntEnum
from rh.util import RHUtils


class RHRace():
    '''Class to hold race management variables.'''
    def __init__(self):
        # setup/options
        self._num_nodes = 0
        self.current_heat = 1 # heat ID
        self.current_round = 1
        self.current_stage = None
        self.node_pilots = {} # current race pilots, by node, filled on heat change
        self._format = None # raceformat object
        # sequence
        self.scheduled = False # Whether to start a race when time
        self.scheduled_time = 0 # Start race when time reaches this value
        self.start_token = False # Check start thread matches correct stage sequence
        # status
        self.race_status = RaceStatus.READY
        self.timer_running = False
        self.start_time = 0 # datetime
        self.start_time_monotonic = 0 # monotonic
        self.start_time_epoch_ms = 0 # ms since 1970-01-01
        self.start_time_delay_secs = 0 # random-length race-start delay
        self.node_laps = {} # current race lap objects, by node
        self.node_splits = {}
        self.node_has_finished = {}
        self.any_races_started = False
        # concluded
        self.finish_time = 0 # Monotonic, updated when race finishes
        self.finish_time_epoch_ms = 0 # ms since 1970-01-01
        self.end_time = 0 # Monotonic, updated when race is stopped
        self.end_time_epoch_ms = 0 # ms since 1970-01-01
        # leaderboard/cache
        self.result_fn = lambda race: None
        self.team_result_fn = lambda race: None
        self.status_message = '' # Race status message (winner, team info)

        self.win_status = WinStatus.NONE # whether race is won
        self.modification_count = 0

        '''
        Lap Object (dict) for node_laps:
            lap_number
            lap_time_stamp
            lap_time
            lap_time_formatted
            source
            deleted
        '''

    @property
    def num_nodes(self):
        return self._num_nodes

    @num_nodes.setter
    def num_nodes(self, new_value):
        self._num_nodes = new_value
        self.reset()

    @property
    def format(self):
        return self._format

    @format.setter
    def format(self, new_race_format):
        self._format = new_race_format
        self.modification_count += 1

    @property
    def results(self):
        return self.result_fn(self)

    @property
    def team_results(self):
        return self.team_result_fn(self)

    def reset(self):
        self.node_laps = {idx: [] for idx in range(self._num_nodes)}
        self.node_splits = {idx: [] for idx in range(self._num_nodes)}
        self.modification_count += 1

    def set_current_pilots(self, rhdata):
        self.node_pilots = {}
        for idx in range(self.num_nodes):
            self.node_pilots[idx] = None

        for heatNode in rhdata.get_heatNodes_by_heat(self.current_heat):
            if heatNode.pilot_id != RHUtils.PILOT_ID_NONE:
                db_pilot = rhdata.get_pilot(heatNode.pilot_id)
                self.node_pilots[heatNode.node_index] = RHPilot(db_pilot)

        self.modification_count += 1

    def init_node_finished_flags(self, heatNodes):
        self.node_has_finished = {}
        for heatNode in heatNodes:
            if heatNode.node_index < self.num_nodes:
                if heatNode.pilot_id != RHUtils.PILOT_ID_NONE:
                    self.node_has_finished[heatNode.node_index] = False
                else:
                    self.node_has_finished[heatNode.node_index] = None

    def set_node_finished_flag(self, node_index):
        self.node_has_finished[node_index] = True

    def get_node_finished_flag(self, node_index):
        return self.node_has_finished.get(node_index, None)

    def check_all_nodes_finished(self):
        return False not in self.node_has_finished.values()

    def get_active_laps(self, late_lap_flag=False):
        # return active (non-deleted) laps objects
        filtered = {}
        if not late_lap_flag:
            for node_index in self.node_laps:
                filtered[node_index] = list(filter(lambda lap : lap['deleted'] == False, self.node_laps[node_index]))
        else:
            for node_index in self.node_laps:
                filtered[node_index] = list(filter(lambda lap : \
                                (lap['deleted'] == False or lap.get('late_lap', False)), self.node_laps[node_index]))
        return filtered

    def any_laps_recorded(self):
        for node_index in range(self._num_nodes):
            if len(self.node_laps[node_index]) > 0:
                return True
        return False


RACE_START_DELAY_EXTRA_SECS = 0.9  # amount of extra time added to prestage time


class RHPilot:
    def __init__(self, db_pilot):
        self._id = db_pilot.id
        self._name = db_pilot.name
        self._callsign = db_pilot.callsign
        self._team = db_pilot.team
        self._phonetic = db_pilot.phonetic if db_pilot.phonetic else db_pilot.callsign

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def callsign(self):
        return self._callsign

    @property
    def phonetic(self):
        return self._phonetic

    @property
    def team(self):
        return self._team


class RaceMode(IntEnum):
    FIXED_TIME = 0
    NO_TIME_LIMIT = 1


class StartBehavior(IntEnum):
    HOLESHOT = 0
    FIRST_LAP = 1
    STAGGERED = 2


class StagingTones(IntEnum):
    TONES_NONE = 0
    TONES_ONE = 1
    TONES_ALL = 2
    TONES_3_2_1 = 3


class WinCondition(IntEnum):
    NONE = 0
    MOST_PROGRESS = 1 # most laps in fastest time
    FIRST_TO_LAP_X = 2
    FASTEST_LAP = 3
    FASTEST_3_CONSECUTIVE = 4
    MOST_LAPS = 5 # lap count only
    MOST_LAPS_OVERTIME = 6 # lap count only, laps and time after T=0


class WinStatus:
    NONE = 0
    TIE = 1
    PENDING_CROSSING = 2
    DECLARED = 3
    OVERTIME = 4


class RaceStatus:
    READY = 0
    STAGING = 3
    RACING = 1
    DONE = 2

