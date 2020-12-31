'''Mock hardware interface layer.'''

import os
import logging
import gevent # For threads and timing
import random
from gevent.lock import BoundedSemaphore # To limit i2c calls
from monotonic import monotonic # to capture read timing

from Node import Node
from BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory

logger = logging.getLogger(__name__)

UPDATE_SLEEP = float(os.environ.get('RH_UPDATE_INTERVAL', '0.5')) # Main update loop delay

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value
MAX_RSSI_VALUE = 999             # reject RSSI readings above this value

class MockInterface(BaseHardwareInterface):
    def __init__(self, *args, **kwargs):
        BaseHardwareInterface.__init__(self)
        self.update_thread = None # Thread for running the main update loop

        # Scans all i2c_addrs to populate nodes array
        self.nodes = [] # Array to hold each node object
        self.data = []
        # i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
        for index in range(int(os.environ.get('RH_NODES', '8'))):
            node = Node() # New node instance
            node.i2c_addr = 2 * index + 8 # Set current loop i2c_addr
            node.index = index
            node.api_valid_flag = True
            node.api_level = 32
            node.enter_at_level = 90
            node.exit_at_level = 80
            self.nodes.append(node) # Add new node to RHInterface
            try:
                f = open("mock_data_{0}.csv".format(index+1))
                logger.info("Loaded mock_data_{0}.csv".format(index+1))
            except IOError:
                f = None
            self.data.append(f)


    #
    # Update Loop
    #

    def start(self):
        if self.update_thread is None:
            self.log('Starting background thread.')
            self.update_thread = gevent.spawn(self.update_loop)

    def stop(self):
        if self.update_thread:
            self.log('Stopping background thread')
            self.update_thread.kill(block=True, timeout=0.5)
            self.update_thread = None

    def update_loop(self):
        try:
            while True:
                self.update()
                gevent.sleep(UPDATE_SLEEP)
        except KeyboardInterrupt:
            logger.info("Update thread terminated by keyboard interrupt")

    def update(self):
        upd_list = []  # list of nodes with new laps (node, new_lap_id, lap_timestamp)
        cross_list = []  # list of nodes with crossing-flag changes
        startThreshLowerNode = None
        for index, node in enumerate(self.nodes):
            if node.frequency:
                readtime = monotonic()

                node_data = self.data[index]
                if node_data:
                    data_line = node_data.readline()
                    if data_line == '':
                        node_data.seek(0)
                        data_line = node_data.readline()
                    data_columns = data_line.split(',')
                    lap_id = int(data_columns[1])
                    ms_val = int(data_columns[2])
                    rssi_val = int(data_columns[3])
                    node.node_peak_rssi = int(data_columns[4])
                    node.pass_peak_rssi = int(data_columns[5])
                    node.loop_time = int(data_columns[6])
                    cross_flag = True if data_columns[7]=='T' else False
                    node.pass_nadir_rssi = int(data_columns[8])
                    node.node_nadir_rssi = int(data_columns[9])
                    pn_history = PeakNadirHistory(node.index)
                    pn_history.peakRssi = int(data_columns[10])
                    pn_history.peakFirstTime = int(data_columns[11])
                    pn_history.peakLastTime = int(data_columns[12])
                    pn_history.nadirRssi = int(data_columns[13])
                    pn_history.nadirFirstTime = int(data_columns[14])
                    pn_history.nadirLastTime = int(data_columns[15])
                    if node.is_valid_rssi(rssi_val):
                        node.current_rssi = rssi_val
                        self.process_lap_stats(node, readtime, lap_id, ms_val, cross_flag, pn_history, cross_list, upd_list)
                    else:
                        self.log('RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node.index+1))

                # check if node is set to temporary lower EnterAt/ExitAt values
                if node.start_thresh_lower_flag:
                    time_now = monotonic()
                    if time_now >= node.start_thresh_lower_time:
                        # if this is the first one found or has earliest time
                        if startThreshLowerNode == None or node.start_thresh_lower_time < \
                                            startThreshLowerNode.start_thresh_lower_time:
                            startThreshLowerNode = node

        # process any nodes with crossing-flag changes
        self.process_crossings(cross_list)

        # process any nodes with new laps detected
        self.process_updates(upd_list)

        if startThreshLowerNode:
            logger.info("For node {0} restoring EnterAt to {1} and ExitAt to {2}"\
                    .format(startThreshLowerNode.index+1, startThreshLowerNode.enter_at_level, \
                            startThreshLowerNode.exit_at_level))
            self.set_enter_at_level(startThreshLowerNode.index, startThreshLowerNode.enter_at_level)
            self.set_exit_at_level(startThreshLowerNode.index, startThreshLowerNode.exit_at_level)
            startThreshLowerNode.start_thresh_lower_flag = False
            startThreshLowerNode.start_thresh_lower_time = 0


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

    def force_end_crossing(self, node_index):
        pass

    def jump_to_bootloader(self):
        self.log("MockInterace - no jump-to-bootloader support")

    def inc_intf_read_block_count(self):
        pass

    def inc_intf_read_error_count(self):
        pass

    def inc_intf_write_block_count(self):
        pass

    def inc_intf_write_error_count(self):
        pass

    def get_intf_total_error_count(self):
        return 0

    def set_intf_error_report_percent_limit(self, percentVal):
        pass

    def get_intf_error_report_str(self, forceFlag=False):
        return None

def get_hardware_interface(*args, **kwargs):
    '''Returns the interface object.'''
    logger.info('Using mock hardware interface')
    return MockInterface(*args, **kwargs)
