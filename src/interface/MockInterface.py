'''Mock hardware interface layer.'''

import os
import logging
import random

import gevent # For threads and timing
from time import monotonic # to capture read timing

from Node import Node
from BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory
from RHInterface import FW_TEXT_BLOCK_SIZE, FW_VERSION_PREFIXSTR, \
                        FW_BUILDDATE_PREFIXSTR, FW_BUILDTIME_PREFIXSTR, \
                        FW_PROCTYPE_PREFIXSTR

logger = logging.getLogger(__name__)

UPDATE_SLEEP = float(os.environ.get('RH_UPDATE_INTERVAL', '0.5')) # Main update loop delay

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value
MAX_RSSI_VALUE = 999             # reject RSSI readings above this value

class MockInterface(BaseHardwareInterface):
    def __init__(self, *args, **kwargs):
        BaseHardwareInterface.__init__(self)
        self.FW_TEXT_BLOCK_SIZE = FW_TEXT_BLOCK_SIZE
        self.FW_VERSION_PREFIXSTR = FW_VERSION_PREFIXSTR
        self.FW_BUILDDATE_PREFIXSTR = FW_BUILDDATE_PREFIXSTR
        self.FW_BUILDTIME_PREFIXSTR = FW_BUILDTIME_PREFIXSTR
        self.FW_PROCTYPE_PREFIXSTR = FW_PROCTYPE_PREFIXSTR
        self.update_thread = None # Thread for running the main update loop

        # Scans all i2c_addrs to populate nodes array
        self.nodes = [] # Array to hold each node object
        self.data = []
        self.mocknodedata = {}
        # i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
        for index in range(int(kwargs['num_nodes'])):
            self.mocknodedata[index] = {
                'lap_number': 0,
                'is_crossing': False,
                'pass_peak_rssi': 0,
                'pass_nadir_rssi': 100,
            }
            node = Node() # New node instance
            node.i2c_addr = 2 * index + 8 # Set current loop i2c_addr
            node.index = index
            node.api_valid_flag = True
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

                if self.mocknodedata[index]['is_crossing']:
                    new_rssi = random.randrange(60,150)
                    pass_peak_rssi = max(self.mocknodedata[index]['pass_peak_rssi'], new_rssi)
                    node_data = {
                        'lap_id': self.mocknodedata[index]['lap_number'],
                        'ms_val': 0,
                        'rssi_val': new_rssi,
                        'node.node_peak_rssi': 100,
                        'node.pass_peak_rssi': pass_peak_rssi,
                        'node.loop_time': 1,
                        'cross_flag': 1,
                        'node.pass_nadir_rssi': self.mocknodedata[index]['pass_nadir_rssi'],
                        'node.node_nadir_rssi': 20,
                        'pn_history.peakRssi': new_rssi,
                        'pn_history.peakFirstTime': 0,
                        'pn_history.peakLastTime': 0,
                        'pn_history.nadirRssi': new_rssi,
                        'pn_history.nadirFirstTime': 0,
                        'pn_history.nadirLastTime': 0
                    }
                    if random.random() < 0.5:
                        self.mocknodedata[index]['is_crossing'] = False
                        self.mocknodedata[index]['pass_nadir_rssi'] = 100
                else:
                    new_rssi = random.randrange(20,40)
                    pass_nadir_rssi = min(self.mocknodedata[index]['pass_nadir_rssi'], new_rssi)
                    node_data = {
                        'lap_id': self.mocknodedata[index]['lap_number'],
                        'ms_val': 0,
                        'rssi_val': new_rssi,
                        'node.node_peak_rssi': 100,
                        'node.pass_peak_rssi': self.mocknodedata[index]['pass_peak_rssi'],
                        'node.loop_time': 1,
                        'cross_flag': 0,
                        'node.pass_nadir_rssi': pass_nadir_rssi,
                        'node.node_nadir_rssi': 20,
                        'pn_history.peakRssi': new_rssi,
                        'pn_history.peakFirstTime': 0,
                        'pn_history.peakLastTime': 0,
                        'pn_history.nadirRssi': new_rssi,
                        'pn_history.nadirFirstTime': 0,
                        'pn_history.nadirLastTime': 0
                    }
                    if random.random() < 0.05:
                        self.mocknodedata[index]['lap_number'] += 1
                        self.mocknodedata[index]['is_crossing'] = True
                        self.mocknodedata[index]['pass_peak_rssi'] = 0


                if node_data:
                    lap_id = node_data['lap_id']
                    ms_val = node_data['ms_val']
                    rssi_val = node_data['rssi_val']
                    node.node_peak_rssi = node_data['node.node_peak_rssi']
                    node.pass_peak_rssi = node_data['node.pass_peak_rssi']
                    node.loop_time = node_data['node.loop_time']
                    cross_flag = node_data['cross_flag']
                    node.pass_nadir_rssi = node_data['node.pass_nadir_rssi']
                    node.node_nadir_rssi = node_data['node.node_nadir_rssi']
                    pn_history = PeakNadirHistory(node.index)
                    pn_history.peakRssi = node_data['pn_history.peakRssi']
                    pn_history.peakFirstTime = node_data['pn_history.peakFirstTime']
                    pn_history.peakLastTime = node_data['pn_history.peakLastTime']
                    pn_history.nadirRssi = node_data['pn_history.nadirRssi']
                    pn_history.nadirFirstTime = node_data['pn_history.nadirFirstTime']
                    pn_history.nadirLastTime = node_data['pn_history.nadirLastTime']
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

    def set_frequency(self, node_index, frequency, *_args):
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

    def send_status_message(self, msgTypeVal, msgDataVal):
        return False

    def send_shutdown_button_state(self, stateVal):
        return False

    def send_shutdown_started_message(self):
        return False

    def send_server_idle_message(self):
        return False

    def get_fwupd_serial_name(self):
        return None

    def close_fwupd_serial_port(self):
        pass

    def get_info_node_obj(self):
        return self.nodes[0] if self.nodes and len(self.nodes) > 0 else None

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
