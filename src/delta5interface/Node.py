'''Node class for the delta 5 interface.'''

class Node:
    '''Node class represents the arduino/rx pair.'''
    def __init__(self):
        self.frequency = 0
        self.current_rssi = 0
        self.trigger_rssi = 0
        self.peak_rssi = 0
        self.last_lap_id = -1
        self.loop_time = 10

    def get_settings_json(self):
        return {
            'frequency': self.frequency,
            'current_rssi': self.current_rssi,
            'trigger_rssi': self.trigger_rssi,
        }

    def get_heartbeat_json(self):
        return {
            'current_rssi': self.current_rssi,
            'trigger_rssi': self.trigger_rssi,
            'peak_rssi': self.peak_rssi
        }
