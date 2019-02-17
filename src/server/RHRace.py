'''Class to hold race management variables.'''

class RHRace():
    '''Class to hold race management variables.'''
    def __init__(self):
        self.num_nodes = 0
        self.current_heat = 1
        self.race_status = 0
        self.timer_running = 0

def get_race_state():
    '''Returns the race object.'''
    return RHRace()
