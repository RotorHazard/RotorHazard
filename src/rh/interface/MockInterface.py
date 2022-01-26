'''Mock hardware interface layer.'''

import os
import gevent
import logging
import json
from monotonic import monotonic  # to capture read timing
import random

from rh.util.RHUtils import FREQUENCY_ID_NONE
from .BaseHardwareInterface import BaseHardwareInterface
from .RHInterface import TIMER_MODE, SCANNER_MODE, RSSI_HISTORY_MODE, RHNodeManager, RHNode, \
    DEFAULT_RECORD_FORMAT, BINARY_RECORD_FORMAT, \
    READ_RSSI, READ_RSSI_STATS, READ_ENTER_STATS, READ_EXIT_STATS, READ_LAP_STATS, READ_ANALYTICS

logger = logging.getLogger(__name__)


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
        self.enter_at_level = 20
        self.exit_at_level = 15
        self.data_reader = None


class MockInterface(BaseHardwareInterface):
    def __init__(self, num_nodes=8, use_datafiles=False, *args, **kwargs):
        super().__init__(update_sleep=0.5)
        self.warn_loop_time = kwargs['warn_loop_time'] if 'warn_loop_time' in kwargs else 1500
        self.use_datafiles = use_datafiles
        self.data_logger_format = os.environ.get('RH_RECORD_FORMAT', DEFAULT_RECORD_FORMAT)

        for index in range(num_nodes):
            manager = MockNodeManager(index)
            node = manager.add_node(index)  # New node instance
            self.node_managers.append(manager)
            self.nodes.append(node)

    def start(self):
        if self.use_datafiles:
            for node in self.nodes:
                if node.data_reader is None:
                    file_format = 'b' if self.data_logger_format == BINARY_RECORD_FORMAT else 't'
                    try:
                        f = open("mock_data_{}.{}".format(node.index+1, self.data_logger_format, 'r'+file_format))
                        logger.info("Loaded {}".format(f.name))
                    except IOError:
                        f = None
                    node.data_reader = f
        super().start()

    def stop(self):
        super().stop()
        for node in self.nodes:
            f = node.data_reader
            if f is not None:
                f.close()
                logger.info("Closed {}".format(f.name))
                node.data_reader = None

    #
    # Update Loop
    #

    def _update(self):
        node_sleep_interval = self.update_sleep/max(len(self.nodes), 1)
        if self.nodes:
            for node in self.nodes:
                if node.scan_enabled and callable(self.read_scan_history):
                    freqs, rssis = self.read_scan_history(node.index)
                    for freq, rssi in zip(freqs, rssis):
                        node.scan_data[freq] = rssi
                elif node.frequency:
                    server_roundtrip = 0
                    node._roundtrip_stats.append(1000*server_roundtrip)

                    data_file = node.data_reader
                    if data_file is not None:
                        now = monotonic()
                        if self.data_logger_format == BINARY_RECORD_FORMAT:
                            cmd = data_file.read(1)
                            if cmd == '':
                                data_file.seek(0)
                                cmd = data_file.read(1)
                            cmd_size = data_file.read(1)
                            cmd_data = data_file.read(cmd_size)
                            node.io_response = node.io_request = now
                            if cmd == READ_RSSI:
                                cmd_values = node.unpack_rssi(cmd_data)
                            elif cmd == READ_ENTER_STATS or cmd == READ_EXIT_STATS:
                                cmd_values = node.unpack_trigger_stats(cmd, cmd_data)
                            elif cmd == READ_LAP_STATS:
                                cmd_values = node.unpack_lap_stats(cmd_data)
                            elif cmd == READ_ANALYTICS:
                                cmd_values = node.unpack_analytics(cmd_data)
                            elif cmd == READ_RSSI_STATS:
                                cmd_values = node.unpack_rssi_stats(cmd_data)
                            else:
                                raise ValueError("Unsupported command: {}".format(cmd))
                        else:
                            data_line = data_file.readline()
                            if data_line == '':
                                data_file.seek(0)
                                data_line = data_file.readline()
                            json_data = json.loads(data_line)
                            cmd = json_data['cmd']
                            cmd_values = json_data['data']
                            if cmd == READ_ENTER_STATS or cmd == READ_EXIT_STATS:
                                cmd_values[1] = now - cmd_values[1]
                            elif cmd == READ_LAP_STATS:
                                cmd_values[1] = now - cmd_values[1]
                            elif cmd == READ_ANALYTICS:
                                cmd_values[4] = now - cmd_values[4]

                        if cmd == READ_RSSI:
                            self.is_new_lap(node, *cmd_values)
                        elif cmd == READ_ENTER_STATS or cmd == READ_EXIT_STATS:
                            is_crossing = (cmd == READ_ENTER_STATS)
                            self.processing_crossing(node, is_crossing, *cmd_values)
                        elif cmd == READ_LAP_STATS:
                            self.process_lap_stats(node, *cmd_values)
                        elif cmd == READ_ANALYTICS:
                            node.current_lifetime, node.loop_time, extremum_rssi, extremum_timestamp, extremum_duration = cmd_values
                            self.append_history(node, extremum_timestamp, extremum_rssi, extremum_duration)
                        elif cmd == READ_RSSI_STATS:
                            node.node_peak_rssi, node.node_nadir_rssi = cmd_values
                        else:
                            raise ValueError("Unsupported command: {}".format(cmd))

                    self.process_capturing(node)

                    self._restore_lowered_thresholds(node)

                    if node.loop_time > self.warn_loop_time:
                        logger.warning("Abnormal loop time for node {}: {}us ({})".format(node, node.loop_time, node._loop_time_stats.formatted(0)))

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
