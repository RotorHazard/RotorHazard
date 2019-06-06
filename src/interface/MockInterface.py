'''Mock interface layer.'''

import gevent # For threads and timing
import random
from gevent.lock import BoundedSemaphore # To limit i2c calls
from monotonic import monotonic # to capture read timing

from Node import Node
from BaseHardwareInterface import BaseHardwareInterface

UPDATE_SLEEP = 0.1 # Main update loop delay

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value
MAX_RSSI_VALUE = 999             # reject RSSI readings above this value
CAP_ENTER_EXIT_AT_MILLIS = 3000  # number of ms for capture of enter/exit-at levels
ENTER_AT_PEAK_MARGIN = 5         # closest that captured enter-at level can be to node peak RSSI

class MockInterface(BaseHardwareInterface):
    def __init__(self):
        BaseHardwareInterface.__init__(self)
        self.update_thread = None # Thread for running the main update loop
        self.pass_record_callback = None # Function added in server.py
        self.hardware_log_callback = None # Function added in server.py
        self.new_enter_or_exit_at_callback = None # Function added in server.py
        self.node_crossing_callback = None # Function added in server.py

        # Scans all i2c_addrs to populate nodes array
        self.nodes = [] # Array to hold each node object
        i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
        for index, addr in enumerate(i2c_addrs):
            node = Node() # New node instance
            node.i2c_addr = addr # Set current loop i2c_addr
            node.index = index
            node.api_valid_flag = True
            node.api_level = 17
            node.enter_at_level = 50
            node.exit_at_level = 100
            self.nodes.append(node) # Add new node to RHInterface

        # Core temperature
        self.core_temp = 30

        # Scan for BME280 devices
        self.bme280_addrs = []
        self.bme280_data = []


    #
    # Class Functions
    #

    def log(self, message):
        '''Hardware log of messages.'''
        if callable(self.hardware_log_callback):
            string = 'Interface: {0}'.format(message)
            self.hardware_log_callback(string)

    #
    # Update Loop
    #

    def start(self):
        if self.update_thread is None:
            self.log('Starting background thread.')
            self.update_thread = gevent.spawn(self.update_loop)

    def update_loop(self):
        try:
            while True:
                self.update()
                gevent.sleep(UPDATE_SLEEP)
        except KeyboardInterrupt:
            print "Update thread terminated by keyboard interrupt"

    def update(self):
        upd_list = []  # list of nodes with new laps (node, new_lap_id, lap_time_ms)
        cross_list = []  # list of nodes with crossing-flag changes
        for node in self.nodes:
            if node.frequency:
                node.current_rssi = 30 + random.randrange(-10, 10)

        # process any nodes with crossing-flag changes
        if len(cross_list) > 0:
            for node in cross_list:
                self.node_crossing_callback(node)

        # process any nodes with new laps detected
        if len(upd_list) > 0:
            if len(upd_list) == 1:  # list contains single item
                item = upd_list[0]
                node = item[0]
                if node.last_lap_id != -1 and callable(self.pass_record_callback):
                    self.pass_record_callback(node, item[2])  # (node, lap_time_ms)
                node.last_lap_id = item[1]  # new_lap_id

            else:  # list contains multiple items; sort so processed in order by lap time
                upd_list.sort(key = lambda i: i[0].lap_ms_since_start)
                for item in upd_list:
                    node = item[0]
                    if node.last_lap_id != -1 and callable(self.pass_record_callback):
                        self.pass_record_callback(node, item[2])  # (node, lap_time_ms)
                    node.last_lap_id = item[1]  # new_lap_id



    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency):
        node = self.nodes[node_index]
        node.debug_pass_count = 0  # reset debug pass count on frequency change
        if frequency:
            node.frequency = frequency
        else:  # if freq=0 (node disabled) then write default freq, but save 0 value
            node.frequency = 0

    def transmit_enter_at_level(self, node, level):
        return level

    def set_enter_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.api_valid_flag:
            node.enter_at_level = self.transmit_enter_at_level(node, level)

    def transmit_exit_at_level(self, node, level):
        return level

    def set_exit_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.api_valid_flag:
            node.exit_at_level = self.transmit_exit_at_level(node, level)

    def set_calibration_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def enable_calibration_mode(self):
        pass  # dummy function; no longer supported

    def set_calibration_offset_global(self, offset):
        return offset  # dummy function; no longer supported

    def set_trigger_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def mark_start_time(self, node_index, start_time):
        node = self.nodes[node_index]

    def mark_start_time_global(self, pi_time):
        bcast_flag = False
        start_time = int(round(pi_time * 1000)) # convert to ms

    def start_capture_enter_at_level(self, node_index):
        node = self.nodes[node_index]
        if node.cap_enter_at_flag is False and node.api_valid_flag:
            node.cap_enter_at_total = 0
            node.cap_enter_at_count = 0
                   # set end time for capture of RSSI level:
            node.cap_enter_at_millis = self.milliseconds() + CAP_ENTER_EXIT_AT_MILLIS
            node.cap_enter_at_flag = True
            return True
        return False

    def start_capture_exit_at_level(self, node_index):
        node = self.nodes[node_index]
        if node.cap_exit_at_flag is False and node.api_valid_flag:
            node.cap_exit_at_total = 0
            node.cap_exit_at_count = 0
                   # set end time for capture of RSSI level:
            node.cap_exit_at_millis = self.milliseconds() + CAP_ENTER_EXIT_AT_MILLIS
            node.cap_exit_at_flag = True
            return True
        return False

    def intf_simulate_lap(self, node_index, ms_val):
        node = self.nodes[node_index]
        node.lap_ms_since_start = ms_val
        self.pass_record_callback(node, 100)

    def force_end_crossing(self, node_index):
        node = self.nodes[node_index]

    def update_environmental_data(self):
        '''Updates environmental data.'''

def get_hardware_interface():
    '''Returns the interface object.'''
    return MockInterface()
