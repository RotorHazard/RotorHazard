'''Mock interface layer.'''

import os
import gevent # For threads and timing
import random
from gevent.lock import BoundedSemaphore # To limit i2c calls
from monotonic import monotonic # to capture read timing

from Node import Node
from BaseHardwareInterface import BaseHardwareInterface

UPDATE_SLEEP = float(os.environ.get('RH_UPDATE_INTERVAL', '0.5')) # Main update loop delay

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value
MAX_RSSI_VALUE = 999             # reject RSSI readings above this value
CAP_ENTER_EXIT_AT_MILLIS = 3000  # number of ms for capture of enter/exit-at levels
ENTER_AT_PEAK_MARGIN = 5         # closest that captured enter-at level can be to node peak RSSI

LAP_SOURCE_REALTIME = 0
LAP_SOURCE_MANUAL = 1
LAP_SOURCE_RECALC = 2

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
        self.data = []
        i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
        for index, addr in enumerate(i2c_addrs):
            node = Node() # New node instance
            node.i2c_addr = addr # Set current loop i2c_addr
            node.index = index
            node.api_valid_flag = True
            node.api_level = 18
            node.enter_at_level = 90
            node.exit_at_level = 80
            self.nodes.append(node) # Add new node to RHInterface
            try:
                f = open("mock_data_{0}.csv".format(index+1))
                print "Loaded mock_data_{0}.csv".format(index+1)
            except IOError:
                f = None
            self.data.append(f)

        # Core temperature
        self.core_temp = 30

        # Scan for INA219 devices
        self.ina219_devices = []
        self.ina219_data = []

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
        for index, node in enumerate(self.nodes):
            if node.frequency:
                readtime = monotonic()

                node_data = self.data[index]
                if not node_data:
                    break;

                data_line = node_data.readline()
                if data_line == '':
                    node_data.seek(0)
                    data_line = node_data.readline()
                data_columns = data_line.split(',')
                lap_id = int(data_columns[1])
                lap_time_ms = int(data_columns[2])
                node.current_rssi = int(data_columns[3])
                node.node_peak_rssi = int(data_columns[4])
                node.pass_peak_rssi = int(data_columns[5])
                node.loop_time = int(data_columns[6])
                cross_flag = True if data_columns[7]=='T' else False
                node.pass_nadir_rssi = int(data_columns[8])
                node.node_nadir_rssi = int(data_columns[9])
                peakRssi = int(data_columns[10])
                peakFirstTime = int(data_columns[11])
                peakLastTime = int(data_columns[12])
                nadirRssi = int(data_columns[13])
                nadirTime = int(data_columns[14])

                if cross_flag != node.crossing_flag:  # if 'crossing' status changed
                    node.crossing_flag = cross_flag
                    if callable(self.node_crossing_callback):
                        cross_list.append(node)

                # if new lap detected for node then append item to updates list
                if lap_id != node.last_lap_id:
                    upd_list.append((node, lap_id, lap_time_ms))

                # check if capturing enter-at level for node
                if node.cap_enter_at_flag:
                    node.cap_enter_at_total += node.current_rssi
                    node.cap_enter_at_count += 1
                    if self.milliseconds() >= node.cap_enter_at_millis:
                        node.enter_at_level = int(round(node.cap_enter_at_total / node.cap_enter_at_count))
                        node.cap_enter_at_flag = False
                              # if too close node peak then set a bit below node-peak RSSI value:
                        if node.node_peak_rssi > 0 and node.node_peak_rssi - node.enter_at_level < ENTER_AT_PEAK_MARGIN:
                            node.enter_at_level = node.node_peak_rssi - ENTER_AT_PEAK_MARGIN
                        self.transmit_enter_at_level(node, node.enter_at_level)
                        if callable(self.new_enter_or_exit_at_callback):
                            self.new_enter_or_exit_at_callback(node, True)

                # check if capturing exit-at level for node
                if node.cap_exit_at_flag:
                    node.cap_exit_at_total += node.current_rssi
                    node.cap_exit_at_count += 1
                    if self.milliseconds() >= node.cap_exit_at_millis:
                        node.exit_at_level = int(round(node.cap_exit_at_total / node.cap_exit_at_count))
                        node.cap_exit_at_flag = False
                        self.transmit_exit_at_level(node, node.exit_at_level)
                        if callable(self.new_enter_or_exit_at_callback):
                            self.new_enter_or_exit_at_callback(node, False)

                # process history data
                if peakRssi > 0:
                    if nadirRssi > 0:
                        # both
                        if peakLastTime < nadirTime:
                            # process peak first
                            if peakFirstTime < peakLastTime:
                                node.history_values.append(peakRssi)
                                node.history_times.append(readtime - (peakFirstTime / 1000.0))
                                node.history_values.append(peakRssi)
                                node.history_times.append(readtime - (peakLastTime / 1000.0))
                            else:
                                node.history_values.append(peakRssi)
                                node.history_times.append(readtime - (peakLastTime / 1000.0))

                            node.history_values.append(nadirRssi)
                            node.history_times.append(readtime - (nadirTime / 1000.0))

                        else:
                            # process nadir first
                            node.history_values.append(nadirRssi)
                            node.history_times.append(readtime - (nadirTime / 1000.0))
                            if peakFirstTime < peakLastTime:
                                node.history_values.append(peakRssi)
                                node.history_times.append(readtime - (peakFirstTime / 1000.0))
                                node.history_values.append(peakRssi)
                                node.history_times.append(readtime - (peakLastTime / 1000.0))
                            else:
                                node.history_values.append(peakRssi)
                                node.history_times.append(readtime - (peakLastTime / 1000.0))

                    else:
                        # peak, no nadir
                        # process peak only
                        if peakFirstTime < peakLastTime:
                            node.history_values.append(peakRssi)
                            node.history_times.append(readtime - (peakFirstTime / 1000.0))
                            node.history_values.append(peakRssi)
                            node.history_times.append(readtime - (peakLastTime / 1000.0))
                        else:
                            node.history_values.append(peakRssi)
                            node.history_times.append(readtime - (peakLastTime / 1000.0))

                elif nadirRssi > 0:
                    # no peak, nadir
                    # process nadir only
                    node.history_values.append(nadirRssi)
                    node.history_times.append(readtime - (nadirTime / 1000.0))

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
                    self.pass_record_callback(node, item[2], LAP_SOURCE_REALTIME)  # (node, lap_time_ms)
                node.last_lap_id = item[1]  # new_lap_id

            else:  # list contains multiple items; sort so processed in order by lap time
                upd_list.sort(key = lambda i: i[0].lap_ms_since_start)
                for item in upd_list:
                    node = item[0]
                    if node.last_lap_id != -1 and callable(self.pass_record_callback):
                        self.pass_record_callback(node, item[2], LAP_SOURCE_REALTIME)  # (node, lap_time_ms)
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
