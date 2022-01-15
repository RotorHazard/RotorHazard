'''Mock hardware interface layer.'''

import os
import gevent
import logging
from monotonic import monotonic  # to capture read timing
import random

from rh.util.RHUtils import FREQUENCY_ID_NONE
from .BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory
from .RHInterface import TIMER_MODE, SCANNER_MODE, RSSI_HISTORY_MODE, RHNodeManager, RHNode

logger = logging.getLogger(__name__)

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value
MAX_RSSI_VALUE = 999             # reject RSSI readings above this value


class MockNodeManager(RHNodeManager):
    TYPE = "Mock"

    def __init__(self, index):
        super().__init__()
        self.api_level = 0
        self.max_rssi_value = 255
        self.addr = 'mock:'+str(index)
        self.firmware_version_str = 'Mock'
        self.firmware_proctype_str = 'Mock'
        self.firmware_timestamp_str = ''

    def _create_node(self, index, multi_node_index):
        node = MockNode(index, multi_node_index, self)
        return node


class MockNode(RHNode):
    def __init__(self, index, multi_node_index, manager):
        super().__init__(index, multi_node_index, manager)


class MockInterface(BaseHardwareInterface):
    def __init__(self, num_nodes=8, use_datafiles=False, *args, **kwargs):
        super().__init__(update_sleep=0.5)
        self.warn_loop_time = kwargs['warn_loop_time'] if 'warn_loop_time' in kwargs else 1500

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
        node_sleep_interval = self.update_sleep/max(len(self.nodes), 1)
        if self.nodes:
            for index, node in enumerate(self.nodes):
                if node.scan_enabled and callable(self.read_scan_history):
                    freqs, rssis = self.read_scan_history(node.index)
                    for freq, rssi in zip(freqs, rssis):
                        node.scan_data[freq] = rssi
                elif node.frequency:
                    server_roundtrip = 0
                    node._roundtrip_stats.append(1000*server_roundtrip)
                    readtime = monotonic()

                    data_file = self.data_files[index] if self.data_files is not None else None
                    if data_file:
                        data_line = data_file.readline()
                        if data_line == '':
                            data_file.seek(0)
                            data_line = data_file.readline()
                        data_columns = data_line.split(',')
                        pass_count = int(data_columns[1])
                        ms_since_lap = int(data_columns[2])
                        rssi_val = int(data_columns[3])
                        node.node_peak_rssi = int(data_columns[4])
                        pass_peak_rssi = int(data_columns[5])
                        node.loop_time = int(data_columns[6])
                        cross_flag = True if data_columns[7]=='T' else False
                        node.pass_nadir_rssi = int(data_columns[8])
                        node.node_nadir_rssi = int(data_columns[9])
                        pn_history = PeakNadirHistory(node, readtime)
                        pn_history.peakRssi = int(data_columns[10])
                        pn_history.peakFirstTime = int(data_columns[11])
                        pn_history.peakLastTime = int(data_columns[12])
                        pn_history.nadirRssi = int(data_columns[13])
                        pn_history.nadirFirstTime = int(data_columns[14])
                        pn_history.nadirLastTime = int(data_columns[15])
                        if node.is_valid_rssi(rssi_val):
                            node.current_rssi = rssi_val
                            pass_timestamp = readtime - (ms_since_lap / 1000.0)
                            self.process_lap_stats(node, pass_count, pass_timestamp, pass_peak_rssi, cross_flag, readtime, rssi_val)
                            self.process_history(node, pn_history)
                            self.process_capturing(node)
                        else:
                            node.bad_rssi_count += 1
                            logger.info('RSSI reading ({}) out of range on Node {}; rejected; count={}'.\
                                     format(rssi_val, node, node.bad_rssi_count))

                    self._restore_lowered_thresholds(node)

                    if node.loop_time > self.warn_loop_time:
                        logger.warning("Abnormal loop time for node {}: {}us ({})".format(node.index+1, node.loop_time, node._loop_time_stats.formatted(0)))

                gevent.sleep(node_sleep_interval)
        else:
            gevent.sleep(node_sleep_interval)


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
            if scan_enabled:
                node.scan_enabled = scan_enabled
                node.saved_frequency = node.frequency
                self.set_frequency(node_index, FREQUENCY_ID_NONE)
                # reset/clear data
                node.scan_data = {}
                self.set_mode(node_index, SCANNER_MODE)
            else:
                self.set_mode(node_index, TIMER_MODE)
                # reset/clear data
                node.scan_data = {}
                # restore original frequency
                self.set_frequency(node_index, node.saved_frequency)
                del node.saved_frequency
                node.scan_enabled = scan_enabled

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
