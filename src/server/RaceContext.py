'''Primary Race management class'''

import RHRace
import logging

logger = logging.getLogger(__name__)

class RaceContext():
    '''Class to hold race management variables.'''
    def __init__(self):
        self.serverstate = ServerState()
        self.interface = None
        self.sensors = None
        self.cluster = None

        self.race = None
        self.last_race = None

        self.rhdata = None

        self.pagecache = None
        self.language = None

        self.events = None
        self.rhui = None

        self.led_manager = None
        self.vrx_manager = None
        self.export_manager = None
        self.import_manager = None
        self.heat_generate_manager = None
        self.raceclass_rank_manager = None
        self.race_points_manager = None

    def branch_race_obj(self):
        self.last_race = RHRace.RHRace(self)

        self.last_race.num_nodes = self.race.num_nodes
        self.last_race.current_heat = self.race.current_heat
        self.last_race.node_pilots = self.race.node_pilots
        self.last_race.node_teams = self.race.node_teams
        self.last_race.format = self.race.format
        self.last_race.profile = self.race.profile
        # sequence
        self.last_race.scheduled = self.race.scheduled
        self.last_race.scheduled_time = self.race.scheduled_time
        self.last_race.start_token = self.race.start_token
        # status
        self.last_race.race_status = self.race.race_status
        self.last_race.timer_running = self.race.timer_running
        self.last_race.stage_time_monotonic = self.race.stage_time_monotonic
        self.last_race.start_time = self.race.start_time
        self.last_race.start_time_monotonic = self.race.start_time_monotonic
        self.last_race.start_time_epoch_ms = self.race.start_time_epoch_ms
        self.last_race.node_laps = self.race.node_laps
        self.last_race.node_has_finished = self.race.node_has_finished
        self.last_race.any_races_started = self.race.any_races_started
        # concluded
        self.last_race.end_time = self.race.end_time
        # leaderboard/cache
        self.last_race.results = self.race.results
        self.last_race.cacheStatus = self.race.cacheStatus
        self.last_race.status_message = self.race.status_message
        self.last_race.team_results = self.race.team_results
        self.last_race.team_cacheStatus = self.race.team_cacheStatus
        self.last_race.win_status = self.race.win_status

class ServerState:
    # epoch time of server launch
    program_start_epoch_time = None
    # monotonic time of server launch
    program_start_mtonic = None
    # offset for converting 'monotonic' time to epoch milliseconds since 1970-01-01
    mtonic_to_epoch_millis_offset = None

    # race format used in secondary mode (must be initialized after database)
    secondary_race_format = None
