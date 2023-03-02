'''Class to hold race management variables.'''

import logging
import RHUtils
import Results
from monotonic import monotonic

logger = logging.getLogger(__name__)

class RHRace():
    '''Class to hold race management variables.'''
    def __init__(self):
        # setup/options
        self.num_nodes = 0
        self.current_heat = 1 # heat ID
        self.node_pilots = {} # current race pilots, by node, filled on heat change
        self.node_teams = {} # current race teams, by node, filled on heat change
        self.format = None # raceformat object
        self.profile = None
        # sequence
        self.scheduled = False # Whether to start a race when time
        self.scheduled_time = 0 # Start race when time reaches this value
        self.start_token = False # Check start thread matches correct stage sequence
        # status
        self.race_status = RaceStatus.READY
        self.timer_running = False
        self.stage_time_monotonic = 0
        self.start_time = 0 # datetime
        self.start_time_monotonic = 0
        self.start_time_epoch_ms = 0 # ms since 1970-01-01
        self.node_laps = {} # current race lap objects, by node
        self.node_has_finished = {}
        self.any_races_started = False
        # concluded
        self.end_time = 0 # Monotonic, updated when race is stopped
        # leaderboard/cache
        self.results = None # current race results
        self.cacheStatus = None # whether cache is valid
        self.status_message = '' # Race status message (winner, team info)

        self.team_results = None # current race results
        self.team_cacheStatus = None # whether cache is valid
        self.win_status = WinStatus.NONE # whether race is won

        '''
        Lap Object (dict) for node_laps:
            lap_number
            lap_time_stamp
            lap_time
            lap_time_formatted
            source
            deleted
        '''

    def init_node_finished_flags(self, heatNodes):
        self.node_has_finished = {}
        for heatNode in heatNodes:
            if heatNode.node_index is not None and heatNode.node_index < self.num_nodes:
                if heatNode.pilot_id != RHUtils.PILOT_ID_NONE:
                    self.node_has_finished[heatNode.node_index] = False
                else:
                    self.node_has_finished[heatNode.node_index] = None

    def set_node_finished_flag(self, node_index, value=True):
        self.node_has_finished[node_index] = value

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
        for node_index in range(self.num_nodes):
            if len(self.node_laps[node_index]) > 0:
                return True
        return False

    def get_results(self, RHData):
        if 'data_ver' in self.cacheStatus and 'build_ver' in self.cacheStatus:
            token = self.cacheStatus['data_ver']
            if self.cacheStatus['data_ver'] == self.cacheStatus['build_ver']:
                # cache hit
                return self.results
            # else: cache miss
        else:
            logger.error('Race cache has invalid status')
            token = monotonic()
            self.clear_results(token)

        # cache rebuild
        logger.debug('Building current race results')
        build = Results.calc_leaderboard(RHData, current_race=self, current_profile=self.profile)
        self.set_results(token, build)
        return build

    def get_team_results(self, RHData):
        if 'data_ver' in self.team_cacheStatus and 'build_ver' in self.team_cacheStatus:
            token = self.team_cacheStatus['data_ver']
            if self.team_cacheStatus['data_ver'] == self.team_cacheStatus['build_ver']:
                # cache hit
                return self.team_results
            # else: cache miss
        else:
            logger.error('Race cache has invalid status')
            token = monotonic()
            self.clear_team_results(token)

        # cache rebuild
        logger.debug('Building current race results')
        build = Results.calc_team_leaderboard(self, RHData)
        self.set_team_results(token, build)
        return build

    def set_results(self, token, results):
        if self.cacheStatus['data_ver'] == token:
            self.cacheStatus['build_ver'] = token
            self.results = results
        return True

    def set_team_results(self, token, results):
        if self.team_cacheStatus['data_ver'] == token:
            self.team_cacheStatus['build_ver'] = token
            self.team_results = results
        return True

    def clear_results(self, token=None):
        if token is None:
            token = monotonic()

        self.cacheStatus = {
            'data_ver': token,
            'build_ver': None
        }
        self.team_cacheStatus = {
            'data_ver': token,
            'build_ver': None
        }
        return True

    def clear_team_results(self, token=None):
        if token is None:
            token = monotonic()

        self.team_cacheStatus = {
            'data_ver': token,
            'build_ver': None
        }
        return True

class StagingTones():
    TONES_NONE = 0
    TONES_ONE = 1
    TONES_ALL = 2
    # TONES_3_2_1 = 3

class StartBehavior():
    HOLESHOT = 0
    FIRST_LAP = 1
    STAGGERED = 2

class WinCondition():
    NONE = 0
    MOST_PROGRESS = 1 # most laps in fastest time
    FIRST_TO_LAP_X = 2
    FASTEST_LAP = 3
    FASTEST_3_CONSECUTIVE = 4
    MOST_LAPS = 5 # lap count only
    MOST_LAPS_OVERTIME = 6 # lap count only, laps and time after T=0

class WinStatus():
    NONE = 0
    TIE = 1
    PENDING_CROSSING = 2
    DECLARED = 3
    OVERTIME = 4

class RaceStatus():
    READY = 0
    STAGING = 3
    RACING = 1
    DONE = 2

