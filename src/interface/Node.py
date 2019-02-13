'''Node class for the RotorHazard interface.'''

class Node:
    '''Node class represents the arduino/rx pair.'''
    def __init__(self):
        self.api_level = 0
        self.api_valid_flag = False
        self.frequency = 0
        self.current_rssi = 0
        self.node_peak_rssi = 0
        self.node_nadir_rssi = 0
        self.pass_peak_rssi = 0
        self.pass_nadir_rssi = 0
        self.last_lap_id = -1
        self.lap_ms_since_start = -1
        self.loop_time = 10
        self.crossing_flag = False
        self.debug_pass_count = 0
        self.enter_at_level = 0
        self.exit_at_level = 0
        self.cap_enter_at_flag = False
        self.cap_enter_at_total = 0
        self.cap_enter_at_count = 0
        self.cap_enter_at_millis = 0
        self.cap_exit_at_flag = False
        self.cap_exit_at_total = 0
        self.cap_exit_at_count = 0
        self.cap_exit_at_millis = 0
        self.history_rssi_min = 0
        self.history_rssi_max = 0
        self.history_lap_time = 0
        self.under_min_lap_count = 0

    def get_settings_json(self):
        return {
            'frequency': self.frequency,
            'current_rssi': self.current_rssi,
            'enter_at_level': self.enter_at_level,
            'exit_at_level': self.exit_at_level
        }

    def get_heartbeat_json(self):
        return {
            'current_rssi': self.current_rssi,
            'node_peak_rssi': self.node_peak_rssi,
            'pass_peak_rssi': self.pass_peak_rssi,
            'pass_nadir_rssi': self.pass_nadir_rssi
        }
