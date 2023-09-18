'''Class to hold race management variables.'''

import logging
import json
import RHUtils
import Results
from monotonic import monotonic
from eventmanager import Evt

logger = logging.getLogger(__name__)

class RHRace():
    '''Class to hold race management variables.'''
    def __init__(self, RaceContext):
        # internal references
        self._racecontext = RaceContext
        self.__ = self._racecontext.language.__
        # setup/options
        self.num_nodes = 0
        self.current_heat = RHUtils.HEAT_ID_NONE # heat ID
        self.node_pilots = {} # current race pilots, by node, filled on heat change
        self.node_teams = {} # current race teams, by node, filled on heat change
        self._format = None # raceformat object
        self._profile = None
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
        self.lap_results = None # current race calculated lap list
        self.lap_cacheStatus = None # whether cache is valid

        self.results = None # current race results
        self.cacheStatus = None # whether cache is valid
        self.status_message = '' # Race status message (winner, team info)

        self.team_results = None # current race results
        self.team_cacheStatus = None # whether cache is valid
        self.win_status = WinStatus.NONE # whether race is won

        self.race_leader_lap = 0  # current race leader
        self.race_leader_pilot_id = RHUtils.PILOT_ID_NONE

        self._seat_colors = []
        self.external_flag = False # is race data controlled externally (from cluster)

        self.clear_results()

        '''
        Lap Object (dict) for node_laps:
            lap_number
            lap_time_stamp
            lap_time
            lap_time_formatted
            source
            deleted
        '''

    def schedule(self, s, m=0):
        if self.race_status != RaceStatus.READY:
            logger.warning("Ignoring request to schedule race: Status not READY")
            return False
            
        if s or m:
            self.scheduled = True
            self.scheduled_time = monotonic() + (int(m) * 60) + int(s)

            self._racecontext.events.trigger(Evt.RACE_SCHEDULE, {
                'scheduled_at': self.scheduled_time
                })

            self._racecontext.rhui.emit_priority_message(self.__("Next race begins in {0:01d}:{1:02d}".format(int(m), int(s))), True)

            logger.info("Scheduling race in {0:01d}:{1:02d}".format(int(m), int(s)))
        else:
            self.scheduled = False
            self._racecontext.events.trigger(Evt.RACE_SCHEDULE_CANCEL)
            self._racecontext.rhui.emit_priority_message(self.__("Scheduled race cancelled"), False)

        self._racecontext.rhui.emit_race_schedule()
        return True

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

    def build_laps_list(self):
        current_laps = []
        for node_idx in range(self.num_nodes):
            node_laps = []
            fastest_lap_time = float("inf")
            fastest_lap_index = None
            last_lap_id = -1
            for idx, lap in enumerate(self.node_laps[node_idx]):
                if (not lap.get('invalid', False)) and \
                    ((not lap['deleted']) or lap.get('late_lap', False)):
                    if not lap.get('late_lap', False):
                        last_lap_id = lap_number = lap['lap_number']
                        if self.format and self.format.start_behavior == StartBehavior.FIRST_LAP:
                            lap_number += 1
                        splits = self.get_splits(node_idx, last_lap_id)
                        if lap['lap_time'] > 0 and idx > 0 and lap['lap_time'] < fastest_lap_time:
                            fastest_lap_time = lap['lap_time']
                            fastest_lap_index = idx
                    else:
                        lap_number = -1
                        last_lap_id += 1
                        splits = self.get_splits(node_idx, last_lap_id)
    
                    node_laps.append({
                        'lap_index': idx,
                        'lap_number': lap_number,
                        'lap_raw': lap['lap_time'],
                        'lap_time': lap['lap_time_formatted'],
                        'lap_time_stamp': lap['lap_time_stamp'],
                        'splits': splits,
                        'late_lap': lap.get('late_lap', False)
                    })

            pilot_data = None
            if node_idx in self.node_pilots:
                pilot = self._racecontext.rhdata.get_pilot(self.node_pilots[node_idx])
                if pilot:
                    pilot_data = {
                        'id': pilot.id,
                        'name': pilot.name,
                        'callsign': pilot.callsign
                    }

            current_laps.append({
                'laps': node_laps,
                'fastest_lap_index': fastest_lap_index,
                'pilot': pilot_data,
                'finished_flag': self.get_node_finished_flag(node_idx)
            })
        current_laps = {
            'node_index': current_laps
        }
        return current_laps

    def get_splits(self, node_idx, lap_id):
        splits = []
        if self._racecontext.cluster:
            for secondary_index in range(len(self._racecontext.cluster.secondaries)):
                if self._racecontext.cluster.isSplitSecondaryAvailable(secondary_index):
                    split = self._racecontext.rhdata.get_lapSplit_by_params(node_idx, lap_id, secondary_index)
                    if split:
                        split_payload = {
                            'split_id': secondary_index,
                            'split_raw': split.split_time,
                            'split_time': split.split_time_formatted,
                            'split_speed': '{0:.2f}'.format(split.split_speed) if split.split_speed is not None else None
                        }
                    else:
                        split_payload = {
                            'split_id': secondary_index,
                            'split_time': '-'
                        }
                    splits.append(split_payload)
        return splits

    def get_lap_results(self):
        if 'data_ver' in self.lap_cacheStatus and 'build_ver' in self.lap_cacheStatus:
            token = self.lap_cacheStatus['data_ver']
            if self.lap_cacheStatus['data_ver'] == self.lap_cacheStatus['build_ver']:
                # cache hit
                return self.lap_results
            # else: cache miss
        else:
            logger.error('Laps cache has invalid status')
            token = monotonic()
            self.clear_lap_results(token)

        # cache rebuild
        # logger.debug('Building current race results')
        build = self.build_laps_list()
        self.set_lap_results(token, build)
        return build

    def get_results(self):
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
        # logger.debug('Building current race results')
        build = Results.calc_leaderboard(self._racecontext.rhdata, current_race=self, current_profile=self.profile)
        self.set_results(token, build)
        return build

    def get_team_results(self):
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
        build = Results.calc_team_leaderboard(self, self._racecontext.rhdata)
        self.set_team_results(token, build)
        return build

    def set_lap_results(self, token, lap_results):
        if self.lap_cacheStatus['data_ver'] == token:
            self.lap_cacheStatus['build_ver'] = token
            self.lap_results = lap_results
        return True

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

    def clear_lap_results(self, token=None):
        if token is None:
            token = monotonic()

        self.lap_cacheStatus = {
            'data_ver': token,
            'build_ver': None
        }
        return True

    def clear_results(self, token=None):
        if token is None:
            token = monotonic()

        self.lap_cacheStatus = {
            'data_ver': token,
            'build_ver': None
        }
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

    @property
    def seat_colors(self):
        return self._seat_colors

    @seat_colors.setter
    def seat_colors(self, value):
        self._seat_colors = value

    def updateSeatColors(self, mode_override=False):
        if self.external_flag:
            return self.seat_colors

        colors = []
        if mode_override is not False:
            mode = mode_override
        else:
            mode = self._racecontext.rhdata.get_optionInt('ledColorMode', 0)

        if self.current_heat == RHUtils.HEAT_ID_NONE:
            practice_flag = True
            if mode == 1:
                mode = 0
        else:
            practice_flag = False

        if mode == 0:
            seatColorOpt = self._racecontext.rhdata.get_option('seatColors', False)
            if seatColorOpt:
                seatColors = json.loads(seatColorOpt)
            else:
                seatColors = [
                    "#0022ff", # Blue
                    "#ff5500", # Orange
                    "#00ff22", # Green
                    "#ff0055", # Magenta
                    "#ddff00", # Yellow
                    "#7700ff", # Purple
                    "#00ffdd", # Teal
                    "#aaaaaa", # White
                ]
        elif mode == 2:
            profile_freqs = json.loads(self.profile.frequencies)

        for node_index in range(self.num_nodes):
            color = '#ffffff'

            if not practice_flag and (not self.node_pilots or self.node_pilots[node_index] == RHUtils.PILOT_ID_NONE):
                color = '#222222'

            elif mode == 0: # by seat
                color = seatColors[node_index % len(seatColors)]

            elif mode == 1: # by pilot
                color = self._racecontext.rhdata.get_pilot(self.node_pilots[node_index]).color

            elif mode == 2: # by frequency, following https://betaflight.com/docs/development/LedStrip#vtx-frequency
                freq = profile_freqs["f"][node_index]

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

            colors.append(RHUtils.hexToColor(color))

        self._seat_colors = colors 

    @property
    def profile(self):
        if self._profile is None:
            stored_profile = self._racecontext.rhdata.get_optionInt('currentProfile')
            self._profile = self._racecontext.rhdata.get_profile(stored_profile)
        return self._profile
    
    @profile.setter
    def profile(self, value):
        self._profile = value

    @property
    def format(self):
        if self._format is None:
            stored_format = self._racecontext.rhdata.get_optionInt('currentFormat')
            if stored_format:
                race_format = self._racecontext.rhdata.get_raceFormat(stored_format)
                if not race_format:
                    race_format = self._racecontext.rhdata.get_first_raceFormat()
                    self._racecontext.rhdata.set_option('currentFormat', race_format.id)
            else:
                race_format =self._racecontext.rhdata.get_first_raceFormat()

            # create a shared instance
            self._format = RHRaceFormat.copy(race_format)
            self._format.id = race_format.id  #pylint: disable=attribute-defined-outside-init
        return self._format

    def getDbRaceFormat(self):
        if self.format is None or RHRaceFormat.isDbBased(self.format):
            stored_format = self._racecontext.rhdata.get_optionInt('currentFormat')
            return self._racecontext.rhdata.get_raceFormat(stored_format)
        else:
            return None

    @format.setter
    def format(self, race_format):
        if self.race_status == RaceStatus.READY:
            if RHRaceFormat.isDbBased(race_format): # stored in DB, not internal race format
                self._racecontext.rhdata.set_option('currentFormat', race_format.id)
                # create a shared instance
                self._format = RHRaceFormat.copy(race_format)
                self._format.id = race_format.id  #pylint: disable=attribute-defined-outside-init
                self.clear_results() # refresh leaderboard
            else:
                self._format = race_format
        else:
            logger.info('Preventing race format change: Race status not READY')

class RHRaceFormat():
    def __init__(self, name, unlimited_time, race_time_sec, lap_grace_sec, staging_fixed_tones, start_delay_min_ms, start_delay_max_ms, staging_delay_tones, number_laps_win, win_condition, team_racing_mode, start_behavior, points_method):
        self.name = name
        self.unlimited_time = unlimited_time
        self.race_time_sec = race_time_sec
        self.lap_grace_sec = lap_grace_sec
        self.staging_fixed_tones = staging_fixed_tones
        self.start_delay_min_ms = start_delay_min_ms
        self.start_delay_max_ms = start_delay_max_ms
        self.staging_delay_tones = staging_delay_tones
        self.number_laps_win = number_laps_win
        self.win_condition = win_condition
        self.team_racing_mode = team_racing_mode
        self.start_behavior = start_behavior
        self.points_method = points_method

    @classmethod
    def copy(cls, race_format):
        return RHRaceFormat(name=race_format.name,
                            unlimited_time=race_format.unlimited_time,
                            race_time_sec=race_format.race_time_sec,
                            lap_grace_sec=race_format.lap_grace_sec,
                            staging_fixed_tones=race_format.staging_fixed_tones,
                            start_delay_min_ms=race_format.start_delay_min_ms,
                            start_delay_max_ms=race_format.start_delay_max_ms,
                            staging_delay_tones=race_format.staging_delay_tones,
                            number_laps_win=race_format.number_laps_win,
                            win_condition=race_format.win_condition,
                            team_racing_mode=race_format.team_racing_mode,
                            start_behavior=race_format.start_behavior,
                            points_method=race_format.points_method)

    @classmethod
    def isDbBased(cls, race_format):
        return hasattr(race_format, 'id')

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
    FASTEST_CONSECUTIVE = 4
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

