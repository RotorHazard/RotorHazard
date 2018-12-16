'''Node class for the delta 5 interface.'''

class Node:
    '''Node class represents the arduino/rx pair.'''
    def __init__(self):
        self.api_level = 0
        self.api_lvl5_flag = False
        self.frequency = 0
        self.current_rssi = 0
        self.trigger_rssi = 0
        self.node_peak_rssi = 0
        self.pass_peak_rssi = 0
        self.node_offs_adj = 0
        self.last_lap_id = -1
        self.loop_time = 10
        self.crossing_flag = False
        self.debug_pass_count = 0

    def get_settings_json(self):
        return {
            'frequency': self.frequency,
            'current_rssi': self.current_rssi,
            'trigger_rssi': self.trigger_rssi
        }

    def get_heartbeat_json(self):
        return {
            'current_rssi': self.current_rssi,
            'trigger_rssi': self.trigger_rssi,
            'pass_peak_rssi': self.pass_peak_rssi
        }
