'''RotorHazard hardware interface layer.'''

import os
import logging
from monotonic import monotonic # to capture read timing

import interface as node_pkg
from .Plugins import Plugins
from interface import pack_8, unpack_8, pack_16, unpack_16, pack_32, unpack_32
from .BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory
from .Node import Node, NodeManager

READ_ADDRESS = 0x00         # Gets i2c address of arduino (1 byte)
READ_MODE = 0x02
READ_FREQUENCY = 0x03       # Gets channel frequency (2 byte)
READ_LAP_STATS = 0x05
READ_LAP_PASS_STATS = 0x0D
READ_LAP_EXTREMUMS = 0x0E
READ_RHFEAT_FLAGS = 0x11     # read feature flags value
# READ_FILTER_RATIO = 0x20    # node API_level>=10 uses 16-bit value
READ_REVISION_CODE = 0x22    # read NODE_API_LEVEL and verification value
READ_NODE_RSSI_PEAK = 0x23   # read 'nodeRssiPeak' value
READ_NODE_RSSI_NADIR = 0x24  # read 'nodeRssiNadir' value
READ_NODE_RSSI_HISTORY = 0x25
READ_NODE_SCAN_HISTORY = 0x26
READ_ENTER_AT_LEVEL = 0x31
READ_EXIT_AT_LEVEL = 0x32
READ_TIME_MILLIS = 0x33      # read current 'millis()' time value
READ_MULTINODE_COUNT = 0x39  # read # of nodes handled by processor
READ_CURNODE_INDEX = 0x3A    # read index of current node for processor
READ_NODE_SLOTIDX = 0x3C     # read node slot index (for multi-node setup)
READ_FW_VERSION = 0x3D       # read firmware version string
READ_FW_BUILDDATE = 0x3E     # read firmware build date string
READ_FW_BUILDTIME = 0x3F     # read firmware build time string
READ_FW_PROCTYPE = 0x40      # read node processor type

WRITE_FREQUENCY = 0x51       # Sets frequency (2 byte)
WRITE_MODE = 0x52
# WRITE_FILTER_RATIO = 0x70   # node API_level>=10 uses 16-bit value
WRITE_ENTER_AT_LEVEL = 0x71
WRITE_EXIT_AT_LEVEL = 0x72
WRITE_CURNODE_INDEX = 0x7A  # write index of current node for processor
SEND_STATUS_MESSAGE = 0x75  # send status message from server to node
FORCE_END_CROSSING = 0x78   # kill current crossing flag regardless of RSSI value
JUMP_TO_BOOTLOADER = 0x7E   # jump to bootloader for flash update

TIMER_MODE = 0
SCANNER_MODE = 1
RSSI_HISTORY_MODE = 2

LAPSTATS_FLAG_CROSSING = 0x01  # crossing is in progress
LAPSTATS_FLAG_PEAK = 0x02      # reported extremum is peak

# upper-byte values for SEND_STATUS_MESSAGE payload (lower byte is data)
STATMSG_SDBUTTON_STATE = 0x01    # shutdown button state (1=pressed, 0=released)
STATMSG_SHUTDOWN_STARTED = 0x02  # system shutdown started
STATMSG_SERVER_IDLE = 0x03       # server-idle tick message

FW_TEXT_BLOCK_SIZE = 16     # length of data returned by 'READ_FW_...' fns

# prefix strings for finding text values in firmware '.bin' files
FW_VERSION_PREFIXSTR = "FIRMWARE_VERSION: "
FW_BUILDDATE_PREFIXSTR = "FIRMWARE_BUILDDATE: "
FW_BUILDTIME_PREFIXSTR = "FIRMWARE_BUILDTIME: "
FW_PROCTYPE_PREFIXSTR = "FIRMWARE_PROCTYPE: "

# features flags for value returned by READ_RHFEAT_FLAGS command
RHFEAT_STM32_MODE = 0x0004      # STM 32-bit processor running multiple nodes
RHFEAT_JUMPTO_BOOTLDR = 0x0008  # JUMP_TO_BOOTLOADER command supported
RHFEAT_IAP_FIRMWARE = 0x0010    # in-application programming of firmware supported
RHFEAT_PH = 0x0100

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value

logger = logging.getLogger(__name__)


def unpack_rssi(node, data):
    if node.manager.api_level >= 18:
        return unpack_8(data)
    else:
        return unpack_16(data) / 2


class RHNodeManager(NodeManager):
    MAX_RETRY_COUNT = 2

    def __init__(self):
        super().__init__()
        self.curr_multi_node_index = None
        self.api_level = 0
        self.api_valid_flag = False
        self.max_rssi_value = 255
        self.rhfeature_flags = 0
        self.firmware_version_str = None
        self.firmware_proctype_str = None
        self.firmware_timestamp_str = None

    def _create_node(self, index, multi_node_index):
        node = RHNode(index, multi_node_index, self)
        node.read_slot_index()
        return node

    def _select_one(self, node):
        return True

    def _select_multi(self, node):
        if self.curr_multi_node_index != node.multi_node_index:
            curr_select = self.select
            self.select = self._select_one
            self.curr_multi_node_index = node.set_and_validate_value_8(WRITE_CURNODE_INDEX, READ_CURNODE_INDEX, node.multi_node_index)
            self.select = curr_select
        return self.curr_multi_node_index == node.multi_node_index

    def read_revision_code(self):
        self.api_level = 0
        try:
            rev_code = self.get_value_16(READ_REVISION_CODE, RHNodeManager.MAX_RETRY_COUNT)
            # check verification code
            if rev_code and (rev_code >> 8) == 0x25:
                self.api_level = rev_code & 0xFF
        except Exception:
            logger.exception('Error fetching READ_REVISION_CODE from {}'.format(self.addr))
        return self.api_level

    def read_address(self):
        node_addr = None
        try:
            node_addr = self.get_value_8(READ_ADDRESS, RHNodeManager.MAX_RETRY_COUNT)
        except Exception:
            logger.exception('Error fetching READ_ADDRESS from {}'.format(self.addr))
        return node_addr

    def read_multinode_count(self):
        multi_count = None
        try:
            multi_count = self.get_value_8(READ_MULTINODE_COUNT, RHNodeManager.MAX_RETRY_COUNT)
        except Exception:
            logger.exception('Error fetching READ_MULTINODE_COUNT from {}'.format(self.addr))
        return multi_count

    def read_feature_flags(self):
        self.rhfeature_flags = 0
        try:
            self.rhfeature_flags = self.get_value_16(READ_RHFEAT_FLAGS, RHNodeManager.MAX_RETRY_COUNT)
        except Exception:
            logger.exception('Error fetching READ_RHFEAT_FLAGS from {}'.format(self.addr))
        return self.rhfeature_flags

    def read_firmware_version(self):
        '''Reads firmware version string'''
        self.firmware_version_str = None
        try:
            data = self.read_command(READ_FW_VERSION, FW_TEXT_BLOCK_SIZE, RHNodeManager.MAX_RETRY_COUNT)
            self.firmware_version_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                          if data != None else None
        except Exception:
            logger.exception('Error fetching READ_FW_VERSION from {}'.format(self.addr))
        return self.firmware_version_str

    def read_string(self, command, max_retries=MAX_RETRY_COUNT):
        data = self.read_command(command, FW_TEXT_BLOCK_SIZE, max_retries)
        return bytearray(data).decode("utf-8").rstrip('\0') \
                                         if data is not None else None

    def read_firmware_proctype(self):
        '''Reads firmware processor-type string'''
        self.firmware_proctype_str = None
        try:
            self.firmware_proctype_str = self.read_string(READ_FW_PROCTYPE, RHNodeManager.MAX_RETRY_COUNT)
        except Exception:
            logger.exception('Error fetching READ_FW_PROCTYPE from {}'.format(self.addr))
        return self.firmware_proctype_str

    def read_firmware_timestamp(self):
        '''Reads firmware build date/time strings'''
        self.firmware_timestamp_str = None
        try:
            data = self.read_string(READ_FW_BUILDDATE, RHNodeManager.MAX_RETRY_COUNT)
            if data is not None:
                self.firmware_timestamp_str = data
                data = self.read_string(READ_FW_BUILDTIME, RHNodeManager.MAX_RETRY_COUNT)
                if data is not None:
                    self.firmware_timestamp_str += " " + data
        except Exception:
            logger.exception('Error fetching READ_FW_DATE/TIME from {}'.format(self.addr))
        return self.firmware_timestamp_str

    def send_status_message(self, msgTypeVal, msgDataVal):
        # send status message to node
        try:
            if self.api_level >= 35:
                data = ((msgTypeVal & 0xFF) << 8) | (msgDataVal & 0xFF)
                self.set_value_16(SEND_STATUS_MESSAGE, data)
                return True
        except Exception:
            logger.exception('Error sending status message to {}'.format(self.addr))
        return False

    def discover_nodes(self, next_index):
        self.read_revision_code()
        if self.api_level > 0:
            if self.api_level >= 10:
                self.api_valid_flag = True  # set flag for newer API functions supported
            if self.api_valid_flag and self.api_level >= 18:
                self.max_rssi_value = 255
            else:
                self.max_rssi_value = 999
    
            if self.api_level >= 32:  # check node API level
                self.read_feature_flags()
                multi_count = self.read_multinode_count()
                if multi_count is None or multi_count > 32:
                    logger.error('Bad READ_MULTINODE_COUNT value {} fetched from {}'.format(multi_count, self.addr))
                    multi_count = 1
                elif multi_count == 0:
                    logger.warning('Fetched READ_MULTINODE_COUNT value of zero from {} (no vrx modules detected)'.format(self.addr))
            else:
                multi_count = 1

            if multi_count > 0:
                self.select = self._select_multi if multi_count > 1 else self._select_one

            info_strs = ["API level={}".format(self.api_level)]
            if self.api_level >= 34:  # read firmware version and build timestamp strings
                if self.read_firmware_version():
                    info_strs.append("fw version={}".format(self.firmware_version_str))
                    if self.api_level >= 35:
                        if self.read_firmware_proctype():
                            info_strs.append("fw type={}".format(self.firmware_proctype_str))
                if self.read_firmware_timestamp():
                    info_strs.append("fw timestamp: {}".format(self.firmware_timestamp_str))
    
            if multi_count == 0:
                logger.info("Device (with zero modules) found at {}: {}".format(self.addr, ', '.join(info_strs)))
            elif multi_count == 1:
                logger.info("Node found at {}: {}".format(self.addr, ', '.join(info_strs)))
                self.add_node(next_index)
            else:
                logger.info("Multi-node (with {} modules) found at {}: {}".format(multi_count, self.addr, ', '.join(info_strs)))
                for _ in range(multi_count):
                    node = self.add_node(next_index)
                    logger.info("Node {} (slot={}) added at {}".format(next_index+1, node.multi_node_slot_index+1, node.addr))
                    next_index += 1
            return True
        else:
            logger.error('Unable to fetch revision code from {}'.format(self.addr))
            return False


class RHNode(Node):
    def __init__(self, index, multi_node_index, manager):
        super().__init__(index, multi_node_index, manager)

    def read_slot_index(self):
        # read node slot index (physical slot position of node on S32_BPill PCB)
        try:
            self.multi_node_slot_index = self.get_value_8(READ_NODE_SLOTIDX)
        except Exception:
            logger.exception('Error fetching READ_NODE_SLOTIDX from node {}'.format(self))
        return self.multi_node_slot_index


class RHInterface(BaseHardwareInterface):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.warn_loop_time = kwargs['warn_loop_time'] if 'warn_loop_time' in kwargs else 1500
        self.FW_TEXT_BLOCK_SIZE = FW_TEXT_BLOCK_SIZE
        self.FW_VERSION_PREFIXSTR = FW_VERSION_PREFIXSTR
        self.FW_BUILDDATE_PREFIXSTR = FW_BUILDDATE_PREFIXSTR
        self.FW_BUILDTIME_PREFIXSTR = FW_BUILDTIME_PREFIXSTR
        self.FW_PROCTYPE_PREFIXSTR = FW_PROCTYPE_PREFIXSTR
        self.fwupd_serial_port = None   # serial port for in-app update of node firmware

        self.node_managers = Plugins(suffix='node')
        self.discover_nodes(*args, **kwargs)

        self.data_loggers = []
        for node in self.nodes:
            node.frequency = node.get_value_16(READ_FREQUENCY)
            if not node.frequency:
                raise RuntimeError('Unable to read frequency value from node {0}'.format(node))

            if node.manager.api_level >= 10:
                node.node_peak_rssi = self.get_value_rssi(node, READ_NODE_RSSI_PEAK)
                if node.manager.api_level >= 13:
                    node.node_nadir_rssi = self.get_value_rssi(node, READ_NODE_RSSI_NADIR)
                node.enter_at_level = self.get_value_rssi(node, READ_ENTER_AT_LEVEL)
                node.exit_at_level = self.get_value_rssi(node, READ_EXIT_AT_LEVEL)
                logger.debug("Node {}: Freq={}, EnterAt={}, ExitAt={}".format(\
                             node, node.frequency, node.enter_at_level, node.exit_at_level))

                if "RH_RECORD_NODE_{0}".format(node.index+1) in os.environ:
                    self.data_loggers.append(open("data_{0}.csv".format(node.index+1), 'w'))
                    logger.info("Data logging enabled for node {0}".format(node))
                else:
                    self.data_loggers.append(None)
            else:
                logger.warning("Node {} has obsolete API_level ({})".format(node, node.manager.api_level))

        for node_manager in self.node_managers:
            if node_manager.rhfeature_flags:
                # if first node manager supports in-app fw update then save port name
                if (not self.fwupd_serial_port) and hasattr(node_manager, 'serial_io') and \
                        (node_manager.rhfeature_flags & (RHFEAT_STM32_MODE|RHFEAT_IAP_FIRMWARE)) != 0:
                    self.fwupd_serial_port = node_manager.serial_io.name
                    break


    def discover_nodes(self, *args, **kwargs):
        self.node_managers.discover(node_pkg, includeOffset=True, *args, **kwargs)
        for manager in self.node_managers:
            self.nodes.extend(manager.nodes)


    #
    # Update Loop
    #

    def _update(self):
        upd_list = []  # list of nodes with new laps (node, new_lap_id, lap_timestamp)
        cross_list = []  # list of nodes with crossing-flag changes
        startThreshLowerNode = None
        for node in self.nodes:
            if node.scan_enabled and callable(self.read_scan_history):
                freqs, rssis = self.read_scan_history(node.index)
                for freq, rssi in zip(freqs, rssis):
                    node.scan_data[freq] = rssi
            elif node.frequency:
                if node.manager.api_valid_flag or node.manager.api_level >= 5:
                    if node.manager.api_level >= 21:
                        data = node.read_command(READ_LAP_STATS, 16)
                    elif node.manager.api_level >= 18:
                        data = node.read_command(READ_LAP_STATS, 19)
                    elif node.manager.api_level >= 17:
                        data = node.read_command(READ_LAP_STATS, 28)
                    elif node.manager.api_level >= 13:
                        data = node.read_command(READ_LAP_STATS, 20)
                    else:
                        data = node.read_command(READ_LAP_STATS, 18)
                    server_roundtrip = node.io_response - node.io_request
                    server_oneway = server_roundtrip / 2
                    readtime = node.io_response - server_oneway
                else:
                    data = node.read_command(READ_LAP_STATS, 17)

                if data != None and len(data) > 0:
                    lap_id = data[0]

                    if node.manager.api_level >= 18:
                        offset_rssi = 3
                        offset_nodePeakRssi = 4
                        offset_passPeakRssi = 5
                        offset_loopTime = 6
                        offset_lapStatsFlags = 8
                        offset_passNadirRssi = 9
                        offset_nodeNadirRssi = 10
                        if node.manager.api_level >= 21:
                            offset_peakRssi = 11
                            offset_peakFirstTime = 12
                            if node.manager.api_level >= 33:
                                offset_peakDuration = 14
                            else:
                                offset_peakLastTime = 14
                            offset_nadirRssi = 11
                            offset_nadirFirstTime = 12
                            if node.manager.api_level >= 33:
                                offset_nadirDuration = 14
                            else:
                                offset_nadirLastTime = 14
                        else:
                            offset_peakRssi = 11
                            offset_peakFirstTime = 12
                            offset_peakLastTime = 14
                            offset_nadirRssi = 16
                            offset_nadirFirstTime = 17
                    else:
                        offset_rssi = 5
                        offset_nodePeakRssi = 7
                        offset_passPeakRssi = 9
                        offset_loopTime = 11
                        offset_lapStatsFlags = 15
                        offset_passNadirRssi = 16
                        offset_nodeNadirRssi = 18
                        offset_peakRssi = 20
                        offset_peakFirstTime = 22
                        offset_nadirRssi = 24
                        offset_nadirFirstTime = 26

                    rssi_val = unpack_rssi(node, data[offset_rssi:])
                    node.current_rssi = rssi_val  # save value (even if invalid so displayed in GUI)
                    if node.is_valid_rssi(rssi_val):

                        cross_flag = None
                        pn_history = None
                        if node.manager.api_valid_flag:  # if newer API functions supported
                            if node.manager.api_level >= 18:
                                ms_val = unpack_16(data[1:])
                                pn_history = PeakNadirHistory(node.index)
                                if node.manager.api_level >= 21:
                                    if data[offset_lapStatsFlags] & LAPSTATS_FLAG_PEAK:
                                        rssi_val = unpack_rssi(node, data[offset_peakRssi:])
                                        if node.is_valid_rssi(rssi_val):
                                            pn_history.peakRssi = rssi_val
                                            pn_history.peakFirstTime = unpack_16(data[offset_peakFirstTime:]) # ms *since* the first peak time
                                            if node.manager.api_level >= 33:
                                                pn_history.peakLastTime = pn_history.peakFirstTime - unpack_16(data[offset_peakDuration:])   # ms *since* the last peak time
                                            else:
                                                pn_history.peakLastTime = unpack_16(data[offset_peakLastTime:])   # ms *since* the last peak time
                                        elif rssi_val > 0:
                                            logger.info('History peak RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node))
                                    else:
                                        rssi_val = unpack_rssi(node, data[offset_nadirRssi:])
                                        if node.is_valid_rssi(rssi_val):
                                            pn_history.nadirRssi = rssi_val
                                            pn_history.nadirFirstTime = unpack_16(data[offset_nadirFirstTime:])
                                            if node.manager.api_level >= 33:
                                                pn_history.nadirLastTime = pn_history.nadirFirstTime - unpack_16(data[offset_nadirDuration:])
                                            else:
                                                pn_history.nadirLastTime = unpack_16(data[offset_nadirLastTime:])
                                        elif rssi_val > 0:
                                            logger.info('History nadir RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node))
                                else:
                                    rssi_val = unpack_rssi(node, data[offset_peakRssi:])
                                    if node.is_valid_rssi(rssi_val):
                                        pn_history.peakRssi = rssi_val
                                        pn_history.peakFirstTime = unpack_16(data[offset_peakFirstTime:]) # ms *since* the first peak time
                                        pn_history.peakLastTime = unpack_16(data[offset_peakLastTime:])   # ms *since* the last peak time
                                    rssi_val = unpack_rssi(node, data[offset_nadirRssi:])
                                    if node.is_valid_rssi(rssi_val):
                                        pn_history.nadirRssi = rssi_val
                                        pn_history.nadirFirstTime = unpack_16(data[offset_nadirFirstTime:])
                                        pn_history.nadirLastTime = pn_history.nadirFirstTime
                            else:
                                ms_val = unpack_32(data[1:])

                            rssi_val = unpack_rssi(node, data[offset_nodePeakRssi:])
                            if node.is_valid_rssi(rssi_val):
                                node.node_peak_rssi = rssi_val
                            rssi_val = unpack_rssi(node, data[offset_passPeakRssi:])
                            if node.is_valid_rssi(rssi_val):
                                node.pass_peak_rssi = rssi_val
                            node.loop_time = unpack_16(data[offset_loopTime:])
                            if data[offset_lapStatsFlags] & LAPSTATS_FLAG_CROSSING:
                                cross_flag = True
                            else:
                                cross_flag = False
                            rssi_val = unpack_rssi(node, data[offset_passNadirRssi:])
                            if node.is_valid_rssi(rssi_val):
                                node.pass_nadir_rssi = rssi_val

                            if node.manager.api_level >= 13:
                                rssi_val = unpack_rssi(node, data[offset_nodeNadirRssi:])
                                if node.is_valid_rssi(rssi_val):
                                    node.node_nadir_rssi = rssi_val

                            if node.manager.api_level >= 18:
                                data_logger = self.data_loggers[node.index]
                                if data_logger:
                                    data_logger.write("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15}\n".format(readtime,lap_id, int(ms_val), node.current_rssi, node.node_peak_rssi, node.pass_peak_rssi, node.loop_time, 'T' if cross_flag else 'F', node.pass_nadir_rssi, node.node_nadir_rssi, pn_history.peakRssi, pn_history.peakFirstTime, pn_history.peakLastTime, pn_history.nadirRssi, pn_history.nadirFirstTime, pn_history.nadirLastTime))

                        else:  # if newer API functions not supported
                            ms_val = unpack_32(data[1:])
                            node.pass_peak_rssi = unpack_rssi(node, data[11:])
                            node.loop_time = unpack_32(data[13:])

                        self.process_lap_stats(node, readtime, lap_id, ms_val, cross_flag, pn_history, cross_list, upd_list)

                    else:
                        node.bad_rssi_count += 1
                        # log the first ten, but then only 1 per 100 after that
                        if node.bad_rssi_count <= 10 or node.bad_rssi_count % 100 == 0:
                            logger.info('RSSI reading ({}) out of range on Node {}; rejected; count={}'.\
                                     format(rssi_val, node, node.bad_rssi_count))

                # check if node is set to temporary lower EnterAt/ExitAt values
                if node.start_thresh_lower_flag:
                    time_now = monotonic()
                    if time_now >= node.start_thresh_lower_time:
                        # if this is the first one found or has earliest time
                        if startThreshLowerNode == None or node.start_thresh_lower_time < \
                                            startThreshLowerNode.start_thresh_lower_time:
                            startThreshLowerNode = node

            if node.loop_time > self.warn_loop_time:
                logger.warning("Abnormal node loop time: {}us".format(node.loop_time))

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
    # Internal helper functions for setting single values
    #

    def set_and_validate_value_rssi(self, node, write_command, read_command, in_value):
        if node.manager.api_level >= 18:
            return node.set_and_validate_value_8(write_command, read_command, in_value)
        else:
            return node.set_and_validate_value_16(write_command, read_command, in_value)

    def get_value_rssi(self, node, command):
        if node.manager.api_level >= 18:
            return node.get_value_8(command)
        else:
            return node.get_value_16(command)

    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency, band=None, channel=None):
        node = self.nodes[node_index]
        node.debug_pass_count = 0  # reset debug pass count on frequency change
        if frequency:
            node.frequency = node.set_and_validate_value_16(
                WRITE_FREQUENCY,
                READ_FREQUENCY,
                frequency)
        else:  # if freq=0 (node disabled) then write frequency value to power down rx module, but save 0 value
            node.set_and_validate_value_16(
                WRITE_FREQUENCY,
                READ_FREQUENCY,
                1111 if node.manager.api_level >= 24 else 5800)
            node.frequency = 0

    def set_mode(self, node_index, mode):
        node = self.nodes[node_index]
        node.mode = node.set_and_validate_value_8(
            WRITE_MODE,
            READ_MODE,
            mode)

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
        return self.set_and_validate_value_rssi(node,
            WRITE_ENTER_AT_LEVEL,
            READ_ENTER_AT_LEVEL,
            level)

    def transmit_exit_at_level(self, node, level):
        return self.set_and_validate_value_rssi(node,
            WRITE_EXIT_AT_LEVEL,
            READ_EXIT_AT_LEVEL,
            level)

    def force_end_crossing(self, node_index):
        node = self.nodes[node_index]
        if node.manager.api_level >= 14:
            node.set_value_8(FORCE_END_CROSSING, 0)

    def jump_to_bootloader(self):
        for node_manager in self.node_managers:
            if (node_manager.rhfeature_flags & RHFEAT_JUMPTO_BOOTLDR) != 0 and hasattr(node_manager, 'jump_to_bootloader'):
                node_manager.jump_to_bootloader()
                return
        logger.info("Unable to find any nodes with jump-to-bootloader support")

    def read_scan_history(self, node_index):
        node = self.nodes[node_index]
        data = node.read_command(READ_NODE_SCAN_HISTORY, 9)
        freqs = []
        rssis = []
        if data is not None and len(data) > 0:
            for i in range(0, len(data), 3):
                freq = unpack_16(data[i:])
                rssi = unpack_8(data[i+2:])
                if freq > 0:
                    freqs.append(freq)
                    rssis.append(rssi)
        return freqs, rssis

    def read_rssi_history(self, node_index):
        node = self.nodes[node_index]
        return node.read_command(READ_NODE_RSSI_HISTORY, 16)

    def send_status_message(self, msgTypeVal, msgDataVal):
        sent_count = 0
        for node_manager in self.node_managers:
            if node_manager.send_status_message(msgTypeVal, msgDataVal):
                sent_count += 1
        return sent_count > 0

    def send_shutdown_button_state(self, stateVal):
        return self.send_status_message(STATMSG_SDBUTTON_STATE, stateVal)

    def send_shutdown_started_message(self):
        return self.send_status_message(STATMSG_SHUTDOWN_STARTED, 0)

    def send_server_idle_message(self):
        return self.send_status_message(STATMSG_SERVER_IDLE, 0)


def get_hardware_interface(*args, **kwargs):
    '''Returns the RotorHazard interface object.'''
    return RHInterface(*args, **kwargs)
