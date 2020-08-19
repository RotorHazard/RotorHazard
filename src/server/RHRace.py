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
        self.node_laps = {} # current race lap objects, by node
        self.node_has_finished = {}
        # concluded
        self.duration_ms = 0 # Duration in seconds, calculated when race is stopped
        self.end_time = 0 # Monotonic, updated when race is stopped
        # leaderboard/cache
        self.results = None # current race results
        self.cacheStatus = CacheStatus.INVALID # whether cache is valid
        self.last_race_results = None # Cache of current race after clearing
        self.last_race_laps = None # Cache of current laps list after clearing
        self.last_race_cacheStatus = CacheStatus.INVALID # whether cache is valid
        self.status_message = '' # Race status message (winner, team info)

        self.team_results = None # current race results
        self.team_cacheStatus = CacheStatus.INVALID # whether cache is valid
        self.win_status = WinStatus.NONE # whether race is won
        self.last_race_team_results = None # Cache of current race team results after clearing
        self.last_race_team_cacheStatus = CacheStatus.INVALID # whether team results cache is valid

        '''
        Lap Object (dict) for node_laps:
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
            filtered[node_index] = filter(lambda lap : lap['deleted'] == False, self.node_laps[node_index])

        return filtered

def get_race_state():
    '''Returns the race object.'''
    return RHRace()

class WinCondition():
    NONE = 0
    MOST_PROGRESS = 1 # most laps in fastest time
    FIRST_TO_LAP_X = 2
    FASTEST_LAP = 3
    FASTEST_3_CONSECUTIVE = 4
    MOST_LAPS = 5 # lap count only

class WinStatus():
    NONE = 0
    TIE = 1
    PENDING_CROSSING = 2
    DECLARED = 3

class RaceStatus():
    READY = 0
    STAGING = 3
    RACING = 1
    DONE = 2

class CacheStatus:
    INVALID = 'invalid'
    VALID = 'valid'
