from monotonic import monotonic

class BaseHardwareInterface(object):

    LAP_SOURCE_REALTIME = 0
    LAP_SOURCE_MANUAL = 1
    LAP_SOURCE_RECALC = 2

    RACE_STATUS_READY = 0
    RACE_STATUS_STAGING = 3
    RACE_STATUS_RACING = 1
    RACE_STATUS_DONE = 2

    def __init__(self):
        self.calibration_threshold = 20
        self.calibration_offset = 10
        self.trigger_threshold = 20
        self.start_time = 1000*monotonic() # millis
        self.filter_ratio = 50
        self.race_status = BaseHardwareInterface.RACE_STATUS_READY

    # returns the elapsed milliseconds since the start of the program
    def milliseconds(self):
       return 1000*(monotonic() - self.start_time)

    #
    # External functions for setting data
    #

    def intf_simulate_lap(self, node_index, ms_val):
        node = self.nodes[node_index]
        node.lap_timestamp = monotonic() - (ms_val / 1000.0)
        self.pass_record_callback(node, node.lap_timestamp, BaseHardwareInterface.LAP_SOURCE_MANUAL)

    def set_race_status(self, race_status):
        self.race_status = race_status

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
