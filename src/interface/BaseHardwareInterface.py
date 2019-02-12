from datetime import datetime
from datetime import timedelta
import time

class BaseHardwareInterface(object):
    def __init__(self):
        self.calibration_threshold = 20
        self.calibration_offset = 10
        self.trigger_threshold = 20
        self.start_time = datetime.now()
        self.filter_ratio = 50

    # returns the elapsed milliseconds since the start of the program
    def milliseconds(self):
       dt = datetime.now() - self.start_time
       ms = round((dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0)
       return ms

    #
    # Get Json Node Data Functions
    #

    def get_settings_json(self):
        return {
            'nodes': [node.get_settings_json() for node in self.nodes],
            'calibration_threshold': self.calibration_threshold,
            'calibration_offset': self.calibration_offset,
            'trigger_threshold': self.trigger_threshold,
            'filter_ratio': self.filter_ratio
        }

    def get_heartbeat_json(self):
        return {
            'current_rssi': [node.current_rssi for node in self.nodes],
            'loop_time': [node.loop_time for node in self.nodes],
            'crossing_flag': [node.crossing_flag for node in self.nodes]
        }

    def get_calibration_threshold_json(self):
        return {
            'calibration_threshold': self.calibration_threshold
        }

    def get_calibration_offset_json(self):
        return {
            'calibration_offset': self.calibration_offset
        }

    def get_trigger_threshold_json(self):
        return {
            'trigger_threshold': self.trigger_threshold
        }

    def get_filter_ratio_json(self):
        return {
            'filter_ratio': self.filter_ratio
        }

    def get_frequency_json(self, node_index):
        node = self.nodes[node_index]
        return {
            'node': node.index,
            'frequency': node.frequency
        }
