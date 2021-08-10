'''Mock hardware interface layer.'''

import os
import logging
from monotonic import monotonic # to capture read timing
import random

from .Node import NodeManager
from .BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory
from .RHInterface import TIMER_MODE, SCANNER_MODE, RSSI_HISTORY_MODE

logger = logging.getLogger(__name__)

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value
MAX_RSSI_VALUE = 999             # reject RSSI readings above this value


class MockNodeManager(NodeManager):
    def __init__(self, index):
        super().__init__()
        self.api_level = 0
        self.api_valid_flag = True
        self.max_rssi_value = 255
        self.addr = 'mock:'+str(index)
        self.firmware_version_str = 'Mock'
        self.firmware_proctype_str = 'Mock'
        self.firmware_timestamp_str = ''


class MockInterface(BaseHardwareInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(update_sleep=0.5)

        self.data = []
        for index in range(int(os.environ.get('RH_NODES', '8'))):
            manager = MockNodeManager(index)
            node = manager.add_node(index) # New node instance
            node.enter_at_level = 90
            node.exit_at_level = 80
            self.node_managers.append(manager)
            self.nodes.append(node)
            try:
                f = open("mock_data_{0}.csv".format(node.index+1))
                logger.info("Loaded mock_data_{0}.csv".format(node.index+1))
            except IOError:
                f = None
            self.data.append(f)


    #
    # Update Loop
    #

    def _update(self):
        upd_list = []  # list of nodes with new laps (node, new_lap_id, lap_timestamp)
        cross_list = []  # list of nodes with crossing-flag changes
        startThreshLowerNode = None
        for index, node in enumerate(self.nodes):
            if node.scan_enabled and callable(self.read_scan_history):
                freqs, rssis = self.read_scan_history(node.index)
                for freq, rssi in zip(freqs, rssis):
                    node.scan_data[freq] = rssi
            elif node.frequency:
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
                        logger.info('RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node.index+1))

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

    def set_frequency(self, node_index, frequency, band=None, channel=None):
        node = self.nodes[node_index]
        node.debug_pass_count = 0  # reset debug pass count on frequency change
        if frequency:
            node.frequency = frequency
        else:  # if freq=0 (node disabled) then write default freq, but save 0 value
            node.frequency = 0

    def set_mode(self, node_index, mode):
        node = self.nodes[node_index]
        node.mode = mode

    def set_frequency_scan(self, node_index, scan_enabled):
        '''Frequency scanning protocol'''
        node = self.nodes[node_index]
        if scan_enabled != node.scan_enabled:
            self.set_mode(node_index, SCANNER_MODE if scan_enabled else TIMER_MODE)
            node.scan_enabled = scan_enabled
            # reset/clear data
            node.scan_data = {}
            # restore original frequency
            if not scan_enabled:
                self.set_frequency(node_index, node.frequency)

    def transmit_enter_at_level(self, node, level):
        return level

    def transmit_exit_at_level(self, node, level):
        return level

    def force_end_crossing(self, node_index):
        pass

    def read_scan_history(self, node_index):
        freqs = list(range(5645, 5945, 5))
        rssis = [random.randint(0, 200) for f in freqs]
        return freqs, rssis

    def read_rssi_history(self, node_index):
        return [random.randint(0, 200) for _ in range(16)]

    def send_status_message(self, msgTypeVal, msgDataVal):
        return False

    def send_shutdown_button_state(self, stateVal):
        return False

    def send_shutdown_started_message(self):
        return False

    def send_server_idle_message(self):
        return False


def get_hardware_interface(*args, **kwargs):
    '''Returns the interface object.'''
    logger.info('Using mock hardware interface')
    return MockInterface(*args, **kwargs)
