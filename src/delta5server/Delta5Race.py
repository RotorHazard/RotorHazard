'''Class to hold race management variables.'''

class Delta5Race():
    '''Class to hold race management variables.'''
    def __init__(self):
        self.num_nodes = 0
        self.current_heat = 1
        self.race_status = 0
        self.lang_id = 2

def get_race_state():
    '''Returns the delta 5 race object.'''
    return Delta5Race()
