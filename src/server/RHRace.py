'''Class to hold race management variables.'''

class RHRace():
    '''Class to hold race management variables.'''
    def __init__(self):
        # setup/options
        self.num_nodes = 0
        self.current_heat = 1 # heat ID
        self.node_pilots = {} # current race pilots, by node, filled on heat change
        self.node_teams = {} # current race teams, by node, filled on heat change
        self.format = None # raceformat object
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
        self.node_laps = {} # current race lap objects, by node
        self.status_tied_str = 'Race is tied; continuing'  # shown when Most Laps Wins race tied
        self.status_crossing = 'Waiting for cross'  # indicator for Most Laps Wins race
        # concluded
        self.duration_ms = 0 # Duration in seconds, calculated when race is stopped
        self.end_time = 0 # Monotonic, updated when race is stopped
        self.laps_winner_name = None  # set to name of winner in first-to-X-laps race
        self.winning_lap_id = 0  # tracks winning lap-id if race tied during first-to-X-laps race
        # leaderboard/cache
        self.results = None # current race results
        self.cacheStatus = CacheStatus.INVALID # whether cache is valid
        self.last_race_results = None # Cache of current race after clearing
        self.last_race_laps = None # Cache of current laps list after clearing
        self.last_race_cacheStatus = CacheStatus.INVALID # whether cache is valid

        '''
        Lap Object (dict):
            lap_number
            lap_time_stamp
            lap_time
            lap_time_formatted
            source
            deleted
        '''

    def get_active_laps(self):
        # return active (non-deleted) laps objects
        filtered = {}
        for node_index in self.node_laps:
            filtered[node_index] = list(filter(lambda lap : lap['deleted'] == False, self.node_laps[node_index]))

        return filtered

def get_race_state():
    '''Returns the race object.'''
    return RHRace()

class WinCondition():
    NONE = 0
    MOST_LAPS = 1
    FIRST_TO_LAP_X = 2
    FASTEST_LAP = 3 # Not yet implemented
    FASTEST_3_CONSECUTIVE = 4 # Not yet implemented

class RaceStatus():
    READY = 0
    STAGING = 3
    RACING = 1
    DONE = 2

class CacheStatus:
    INVALID = 'invalid'
    VALID = 'valid'
