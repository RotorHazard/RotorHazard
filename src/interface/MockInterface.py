'''Mock hardware interface layer.'''

import os
import logging

import gevent # For threads and timing
from time import monotonic # to capture read timing

from Node import Node
from BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory, MarshalType
import MockSignal
from RHInterface import FW_TEXT_BLOCK_SIZE, FW_VERSION_PREFIXSTR, \
                        FW_BUILDDATE_PREFIXSTR, FW_BUILDTIME_PREFIXSTR, \
                        FW_PROCTYPE_PREFIXSTR

logger = logging.getLogger(__name__)

UPDATE_SLEEP_ENV = os.environ.get('RH_UPDATE_INTERVAL')  # main update loop delay; overrides the 'MOCK_UPDATE_INTERVAL' setting
DEFAULT_UPDATE_SLEEP = 0.5
MIN_UPDATE_SLEEP = 0.01

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
        self.marshal_type = MarshalType.FULL_RSSI

        self.config = kwargs['config'] # provides access to RH config
        self.nodes = [] # Array to hold each node object
        self.signal_name = None  # name of the active signal provider
        self.signal_provider = None
        self.signal_fallback = False  # whether the setting names an unregistered signal
        self.signal_error_logged = False
        # i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
        for index in range(int(kwargs['num_nodes'])):
            node = Node() # New node instance
            node.i2c_addr = 2 * index + 8 # Set current loop i2c_addr
            node.index = index
            node.api_valid_flag = True
            node.enter_at_level = 90
            node.exit_at_level = 80
            self.nodes.append(node) # Add new node to RHInterface


    #
    # Update Loop
    #

    def start(self):
        if self.update_thread is None:
            self.log('Starting background thread')
            self.update_thread = gevent.spawn(self.update_loop)

    def stop(self):
        if self.update_thread:
            self.log('Stopping background thread')
            self.update_thread.kill(block=True, timeout=0.5)
            self.update_thread = None
        if self.signal_provider:
            self.signal_provider.stop()
            self.signal_provider = None
            self.signal_name = None

    def get_signal_provider(self):
        '''The provider named by the 'MOCK_NODE_SIGNAL' setting, switching to it if it changed.'''
        name = str(self.config.get_item('GENERAL', 'MOCK_NODE_SIGNAL') or 0)
        entry = MockSignal.get_signal(name)
        # an unregistered name (e.g. its plugin not loaded) gives no signal, until it is registered
        if name != self.signal_name or (entry and self.signal_fallback):
            if not entry:
                logger.warning("Mock signal '{}' not registered; using none".format(name))
                entry = MockSignal.get_signal('0')
            if self.signal_provider:
                self.signal_provider.stop()
            self.signal_name = name
            self.signal_fallback = entry.name != name
            self.signal_provider = entry.provider
            self.signal_error_logged = False
            logger.info("Mock node signal: {}".format(entry.label))
            self.signal_provider.start()
        return self.signal_provider

    def set_race_status(self, race_status):
        super().set_race_status(race_status)
        if self.signal_provider:
            try:
                self.signal_provider.on_race_status(race_status)
            except Exception:
                logger.exception("Error in mock signal '{}' race status handler".format(self.signal_name))

    def get_update_interval(self):
        '''Seconds between updates, from 'RH_UPDATE_INTERVAL' if set, else the 'MOCK_UPDATE_INTERVAL' setting.'''
        try:
            interval = float(UPDATE_SLEEP_ENV or self.config.get_item('GENERAL', 'MOCK_UPDATE_INTERVAL') or DEFAULT_UPDATE_SLEEP)
        except (TypeError, ValueError):
            interval = DEFAULT_UPDATE_SLEEP
        return max(interval, MIN_UPDATE_SLEEP)

    def update_loop(self):
        try:
            while True:
                self.update()
                gevent.sleep(self.get_update_interval())
        except KeyboardInterrupt:
            logger.info("Update thread terminated by keyboard interrupt")

    def update(self):
        upd_list = []  # list of nodes with new laps (node, new_lap_id, lap_timestamp)
        cross_list = []  # list of nodes with crossing-flag changes
        startThreshLowerNode = None

        provider = self.get_signal_provider()
        self.marshal_type = getattr(provider, 'marshal_type', MarshalType.FULL_RSSI)

        for index, node in enumerate(self.nodes):
            if node.frequency:
                readtime = monotonic()

                try:
                    result = provider.read(node, readtime)
                except Exception:
                    result = None
                    if not self.signal_error_logged:
                        self.signal_error_logged = True
                        logger.exception("Error reading mock signal '{}' for node {}".format(self.signal_name, index+1))

                samples = result if isinstance(result, (list, tuple)) else ([result] if result else [])
                for sample in samples:
                    if len(samples) > 1:
                        # each reading's crossing and pass is handled before the next
                        node_cross_list = []
                        node_upd_list = []
                        self.apply_sample(node, sample, readtime, node_cross_list, node_upd_list)
                        self.process_crossings(node_cross_list)
                        self.process_updates(node_upd_list)
                    else:
                        self.apply_sample(node, sample, readtime, cross_list, upd_list)

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


    def apply_sample(self, node, sample, readtime, cross_list, upd_list):
        '''Takes one reading into the node, as the hardware interface does with a node's report.'''
        node.node_peak_rssi = sample.node_peak_rssi
        node.pass_peak_rssi = sample.pass_peak_rssi
        node.loop_time = sample.loop_time
        node.pass_nadir_rssi = sample.pass_nadir_rssi
        node.node_nadir_rssi = sample.node_nadir_rssi
        if sample.history_flag:
            pn_history = PeakNadirHistory(node.index)
            pn_history.peakRssi = sample.peak_rssi
            pn_history.peakFirstTime = sample.peak_first_time
            pn_history.peakLastTime = sample.peak_last_time
            pn_history.nadirRssi = sample.nadir_rssi
            pn_history.nadirFirstTime = sample.nadir_first_time
            pn_history.nadirLastTime = sample.nadir_last_time
        else:
            pn_history = None
        if node.is_valid_rssi(sample.rssi):
            node.current_rssi = sample.rssi
            self.process_lap_stats(node, sample.read_time if sample.read_time is not None else readtime,
                                   sample.lap_id, sample.ms_val, sample.cross_flag, pn_history, cross_list, upd_list)
        else:
            self.log('RSSI reading ({0}) out of range on Node {1}; rejected'.format(sample.rssi, node.index+1))

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
