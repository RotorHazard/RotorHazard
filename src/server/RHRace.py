'''Class to hold race management variables.'''

class RHRace():
    '''Class to hold race management variables.'''
    def __init__(self):
        self.num_nodes = 0
        self.current_heat = 1
        self.race_status = 0
        self.timer_running = 0
        self.start_time = 0 # datetime
        self.format = None

        self.start_time_monotonic = 0
        self.start_token = False # Check start thread matches correct stage sequence
        self.duration_ms = 0 # Calculated when race is stopped
        self.end_time = 0 # Updated when race is stopped

        self.scheduled = False # Whether to start a race when time
        self.scheduled_time = 0 # Start race when time reaches this value

        self.laps_winner_name = None  # set to name of winner in first-to-X-laps race
        self.status_tied_str = 'Race is tied; continuing'  # shown when Most Laps Wins race tied
        self.status_crossing = 'Waiting for cross'  # indicator for Most Laps Wins race

        self.node_laps = [] # contains current race laps, by node

    def get_active_laps(self):
        filtered = []
        for node in self.node_laps:
            filtered.append(filter(lambda lap : lap['deleted'] == False, node))

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


'''
RACE.node_laps[node.index].append({
    'pilot_id': pilot_id,
    'lap_id': lap_id,
    'lap_time_stamp': lap_time_stamp,
    'lap_time': lap_time,
    'lap_time_formatted': time_format(lap_time),
    'source': source,
    'deleted': False
})

# non-database model
CurrentLap = []

class LapObj():
    id =
    node_index =
    pilot_id =
    lap_id =
    lap_time_stamp =
    lap_time =
    lap_time_formatted =
    source =
    deleted =
'''