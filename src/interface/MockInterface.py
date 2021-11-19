'''Mock hardware interface layer.'''

import os
import logging
from monotonic import monotonic  # to capture read timing
import random

from .Node import NodeManager
from .BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory
from .RHInterface import TIMER_MODE, SCANNER_MODE, RSSI_HISTORY_MODE

logger = logging.getLogger(__name__)

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value
MAX_RSSI_VALUE = 999             # reject RSSI readings above this value


class MockNodeManager(NodeManager):
    TYPE = "Mock"

    def __init__(self, index):
        super().__init__()
        self.api_level = 0
        self.max_rssi_value = 255
        self.addr = 'mock:'+str(index)
        self.firmware_version_str = 'Mock'
        self.firmware_proctype_str = 'Mock'
        self.firmware_timestamp_str = ''


class MockInterface(BaseHardwareInterface):
    def __init__(self, num_nodes=8, use_datafiles=False, *args, **kwargs):
        super().__init__(update_sleep=0.5)

        self.data_files = [None]*num_nodes if use_datafiles else None
        for index in range(num_nodes):
            manager = MockNodeManager(index)
            node = manager.add_node(index)  # New node instance
            node.enter_at_level = 90
            node.exit_at_level = 80
            self.node_managers.append(manager)
            self.nodes.append(node)

    def start(self):
        if self.data_files is not None:
            for node in self.nodes:
                if not self.data_files[node.index]:
                    try:
                        f = open("mock_data_{0}.csv".format(node.index+1))
                        logger.info("Loaded {}".format(f.name))
                    except IOError:
                        f = None
                    self.data_files[node.index] = f
        super().start()

    def stop(self):
        super().stop()
        if self.data_files is not None:
            for i,f in enumerate(self.data_files):
                if f is not None:
                    f.close()
                    logger.info("Closed {}".format(f.name))
                    self.data_files[i] = None

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

                data_file = self.data_files[index] if self.data_files is not None else None
                if data_file:
                    data_line = data_file.readline()
                    if data_line == '':
                        data_file.seek(0)
                        data_line = data_file.readline()
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
    num_nodes = int(os.environ.get('RH_NODES', '8'))
    return MockInterface(num_nodes=num_nodes, use_datafiles=True, *args, **kwargs)
