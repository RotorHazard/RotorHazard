'''RotorHazard hardware interface layer.'''

import os
import logging
from monotonic import monotonic # to capture read timing

import interface as node_pkg
from .Plugins import Plugins
from interface import pack_8, unpack_8, pack_16, unpack_16, pack_32, unpack_32
from .BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory
from .Node import SharedIOLine

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

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value

logger = logging.getLogger(__name__)

def unpack_rssi(node, data):
    if node.api_level >= 18:
        return unpack_8(data)
    else:
        return unpack_16(data) / 2


class RHInterface(BaseHardwareInterface):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.FW_TEXT_BLOCK_SIZE = FW_TEXT_BLOCK_SIZE
        self.FW_VERSION_PREFIXSTR = FW_VERSION_PREFIXSTR
        self.FW_BUILDDATE_PREFIXSTR = FW_BUILDDATE_PREFIXSTR
        self.FW_BUILDTIME_PREFIXSTR = FW_BUILDTIME_PREFIXSTR
        self.FW_PROCTYPE_PREFIXSTR = FW_PROCTYPE_PREFIXSTR
        self.update_thread = None      # Thread for running the main update loop
        self.fwupd_serial_obj = None   # serial object for in-app update of node firmware

        self.nodes = Plugins(suffix='node')
        self.discover_nodes(*args, **kwargs)

        self.data_loggers = []
        for node in self.nodes:
            node.frequency = node.get_value_16(READ_FREQUENCY)
            if not node.frequency:
                raise RuntimeError('Unable to read frequency value from node {0}'.format(node))

            if node.api_level >= 10:
                node.node_peak_rssi = self.get_value_rssi(node, READ_NODE_RSSI_PEAK)
                if node.api_level >= 13:
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
                logger.warning("Node {} has obsolete API_level ({})".format(node, node.api_level))
            if node.api_level >= 32:
                flags_val = node.get_value_16(READ_RHFEAT_FLAGS)
                if flags_val:
                    node.rhfeature_flags = flags_val
                    # if first node that supports in-app fw update then save port name
                    if (not self.fwupd_serial_obj) and hasattr(node, 'serial') and \
                            (node.rhfeature_flags & (RHFEAT_STM32_MODE|RHFEAT_IAP_FIRMWARE)) != 0:
                        self.set_fwupd_serial_obj(node.serial)


    def discover_nodes(self, *args, **kwargs):
        self.nodes.discover(node_pkg, includeOffset=True, *args, **kwargs)


    #
    # Update Loop
    #

    def _update(self):
        upd_list = []  # list of nodes with new laps (node, new_lap_id, lap_timestamp)
        cross_list = []  # list of nodes with crossing-flag changes
        startThreshLowerNode = None
        for node in self.nodes:
            if node.frequency:
                if node.api_valid_flag or node.api_level >= 5:
                    if node.api_level >= 21:
                        data = node.read_block(READ_LAP_STATS, 16)
                    elif node.api_level >= 18:
                        data = node.read_block(READ_LAP_STATS, 19)
                    elif node.api_level >= 17:
                        data = node.read_block(READ_LAP_STATS, 28)
                    elif node.api_level >= 13:
                        data = node.read_block(READ_LAP_STATS, 20)
                    else:
                        data = node.read_block(READ_LAP_STATS, 18)
                    server_roundtrip = node.io_response - node.io_request
                    server_oneway = server_roundtrip / 2
                    readtime = node.io_response - server_oneway
                else:
                    data = node.read_block(READ_LAP_STATS, 17)

                if data != None and len(data) > 0:
                    lap_id = data[0]

                    if node.api_level >= 18:
                        offset_rssi = 3
                        offset_nodePeakRssi = 4
                        offset_passPeakRssi = 5
                        offset_loopTime = 6
                        offset_lapStatsFlags = 8
                        offset_passNadirRssi = 9
                        offset_nodeNadirRssi = 10
                        if node.api_level >= 21:
                            offset_peakRssi = 11
                            offset_peakFirstTime = 12
                            if node.api_level >= 33:
                                offset_peakDuration = 14
                            else:
                                offset_peakLastTime = 14
                            offset_nadirRssi = 11
                            offset_nadirFirstTime = 12
                            if node.api_level >= 33:
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
                        offset_peakTime = 22
                        offset_nadirRssi = 24
                        offset_nadirFirstTime = 26

                    rssi_val = unpack_rssi(node, data[offset_rssi:])
                    node.current_rssi = rssi_val  # save value (even if invalid so displayed in GUI)
                    if node.is_valid_rssi(rssi_val):

                        cross_flag = None
                        pn_history = None
                        if node.api_valid_flag:  # if newer API functions supported
                            if node.api_level >= 18:
                                ms_val = unpack_16(data[1:])
                                pn_history = PeakNadirHistory(node.index)
                                if node.api_level >= 21:
                                    if data[offset_lapStatsFlags] & LAPSTATS_FLAG_PEAK:
                                        rssi_val = unpack_rssi(node, data[offset_peakRssi:])
                                        if node.is_valid_rssi(rssi_val):
                                            pn_history.peakRssi = rssi_val
                                            pn_history.peakFirstTime = unpack_16(data[offset_peakFirstTime:]) # ms *since* the first peak time
                                            if node.api_level >= 33:
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
                                            if node.api_level >= 33:
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

                            if node.api_level >= 13:
                                rssi_val = unpack_rssi(node, data[offset_nodeNadirRssi:])
                                if node.is_valid_rssi(rssi_val):
                                    node.node_nadir_rssi = rssi_val

                            if node.api_level >= 18:
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

            if node.loop_time > 1500:
                logger.warning("Abnormal node loop time: {}".format(node.loop_time))

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
        if node.api_level >= 18:
            return node.set_and_validate_value_8(write_command, read_command, in_value)
        else:
            return node.set_and_validate_value_16(write_command, read_command, in_value)

    def get_value_rssi(self, node, command):
        if node.api_level >= 18:
            return node.get_value_8(command)
        else:
            return node.get_value_16(command)

    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency):
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
                1111 if node.api_level >= 24 else 5800)
            node.frequency = 0

    def set_mode(self, node_index, mode):
        node = self.nodes[node_index]
        node.mode = node.set_and_validate_value_8(
            WRITE_MODE,
            READ_MODE,
            mode)

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
        if node.api_level >= 14:
            node.set_value_8(FORCE_END_CROSSING, 0)

    def jump_to_bootloader(self):
        for node in self.nodes:
            if (node.rhfeature_flags & RHFEAT_JUMPTO_BOOTLDR) != 0 and hasattr(node, 'jump_to_bootloader'):
                node.jump_to_bootloader()
                return
        logger.info("Unable to find any nodes with jump-to-bootloader support")

    def read_rssi_history(self, node_index):
        node = self.nodes[node_index]
        data = node.read_block(READ_NODE_SCAN_HISTORY, 9)
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

    def send_status_message(self, msgTypeVal, msgDataVal):
        if len(self.nodes) > 0:
            return self.nodes[0].send_status_message(msgTypeVal, msgDataVal)
        return False

    def send_shutdown_button_state(self, stateVal):
        return self.send_status_message(STATMSG_SDBUTTON_STATE, stateVal)

    def send_shutdown_started_message(self):
        return self.send_status_message(STATMSG_SHUTDOWN_STARTED, 0)

    def send_server_idle_message(self):
        return self.send_status_message(STATMSG_SERVER_IDLE, 0)

    def set_fwupd_serial_obj(self, serial_obj):
        self.fwupd_serial_obj = serial_obj

    def set_mock_fwupd_serial_obj(self, port_name):
        serial_obj = type('', (), {})()  # empty base object
        def mock_no_op():
            pass
        serial_obj.name = port_name
        serial_obj.open = mock_no_op
        serial_obj.close = mock_no_op
        self.fwupd_serial_obj = serial_obj

    def get_fwupd_serial_name(self):
        return self.fwupd_serial_obj.name if self.fwupd_serial_obj else None

    def close_fwupd_serial_port(self):
        try:
            if self.fwupd_serial_obj:
                self.fwupd_serial_obj.close()
        except Exception:
            logger.exception("Error closing FW node serial port")


def send_status_message(node, msgTypeVal, msgDataVal):
    # send status message to node
    try:
        if node.api_level >= 35:
            data = ((msgTypeVal & 0xFF) << 8) | (msgDataVal & 0xFF)
#                logger.info('Sending status message to serial node {}: 0x{:04X}'.format(self, data))
            node.write_block_any(SEND_STATUS_MESSAGE, pack_16(data))
            return True
    except Exception:
        logger.exception('Error sending status message to node {}'.format(node))
    return False

def read_node_slot_index(node):
    # read node slot index (physical slot position of node on S32_BPill PCB)
    try:
        node.multi_node_slot_index = node.get_value_8(READ_NODE_SLOTIDX)
    except Exception:
        logger.exception('Error fetching READ_NODE_SLOTIDX for node {}'.format(node))
    return node.multi_node_slot_index

def read_multinode_count(node):
    try:
        data = node.read_block_any(READ_MULTINODE_COUNT, 1, 2)
        multi_count = unpack_8(data) if data != None else None
    except Exception:
        logger.exception('Error fetching READ_MULTINODE_COUNT for node {}'.format(node))
        multi_count = None
    return multi_count

def read_revision_code(node):
    try:
        data = node.read_block_any(READ_REVISION_CODE, 2, 2)
        rev_code = unpack_16(data) if data != None else None
        # check verification code
        if rev_code and (rev_code >> 8) == 0x25:
            node.api_level = rev_code & 0xFF
            return node.api_level
    except Exception:
        logger.exception('Error fetching READ_REVISION_CODE for node {}'.format(node))
    return None

def read_firmware_version(node):
    # read firmware version string
    try:
        data = node.read_block_any(READ_FW_VERSION, FW_TEXT_BLOCK_SIZE, 2)
        node.firmware_version_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                      if data != None else None
    except Exception:
        logger.exception('Error fetching READ_FW_VERSION for node {}'.format(node))
    return node.firmware_version_str

def read_firmware_proctype(node):
    # read firmware processor-type string
    try:
        data = node.read_block_any(READ_FW_PROCTYPE, FW_TEXT_BLOCK_SIZE, 2)
        node.firmware_proctype_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                     if data != None else None
    except Exception:
        logger.exception('Error fetching READ_FW_PROCTYPE for node {}'.format(node))
    return node.firmware_proctype_str

def read_firmware_timestamp(node):
    # read firmware build date/time strings
    try:
        data = node.read_block_any(READ_FW_BUILDDATE, FW_TEXT_BLOCK_SIZE, 2)
        if data != None:
            node.firmware_timestamp_str = bytearray(data).decode("utf-8").rstrip('\0')
            data = node.read_block_any(READ_FW_BUILDTIME, FW_TEXT_BLOCK_SIZE, 2)
            if data != None:
                node.firmware_timestamp_str += " " + bytearray(data).decode("utf-8").rstrip('\0')
        else:
            node.firmware_timestamp_str = None
    except Exception:
        logger.exception('Error fetching READ_FW_DATE/TIME for node {}'.format(node))
    return node.firmware_timestamp_str

def build_nodes(node):
    nodes = []
    if node and node.api_level > 0:
        if node.api_level >= 10:
            node.api_valid_flag = True  # set flag for newer API functions supported
        if node.api_valid_flag and node.api_level >= 18:
            node.max_rssi_value = 255
        else:
            node.max_rssi_value = 999

        if node.api_level >= 32:  # check node API level
            multi_count = read_multinode_count(node)
            if multi_count is None or multi_count > 32:
                logger.error('Bad READ_MULTINODE_COUNT value {} fetched from node {}'.format(multi_count, node))
                multi_count = 1
            elif multi_count == 0:
                logger.warning('Fetched READ_MULTINODE_COUNT value of zero from node {} (no vrx modules detected)'.format(node))
        else:
            multi_count = 1

        info_strs = ["API level={}".format(node.api_level)]
        if node.api_level >= 34:  # read firmware version and build timestamp strings
            if read_firmware_version(node):
                info_strs.append("fw version={}".format(node.firmware_version_str))
                if node.api_level >= 35:
                    if read_firmware_proctype(node):
                        info_strs.append("fw type={}".format(node.firmware_proctype_str))
            if read_firmware_timestamp(node):
                info_strs.append("fw timestamp: {}".format(node.firmware_timestamp_str))

        if multi_count == 0:
            logger.info("Node (with zero modules) found at {}: {}".format(node.addr, ', '.join(info_strs)))
        elif multi_count == 1:
            logger.info("Node {} found at {}: {}".format(node.addr, ', '.join(info_strs)))
            nodes.append(node)
        else:
            logger.info("Multi-node (with {} modules) found at {}: {}".format(multi_count, node.addr, ', '.join(info_strs)))
            node.io_line = SharedIOLine(WRITE_CURNODE_INDEX, READ_CURNODE_INDEX)
            node.multi_node_index = 0
            node.read_node_slot_index()
            logger.debug("Node {} (slot={}) added at {}".format(node, node.multi_node_slot_index+1, node.addr))
            nodes.append(node)
            next_index = node.index + 1
            for multi_idx in range(1, multi_count):
                other_node = node.create_multi_node(next_index, multi_idx)
                other_node.read_node_slot_index()
                logger.debug("Node {} (slot={}) added at {}".format(node, node.multi_node_slot_index+1, node.addr))
                nodes.append(other_node)
                next_index += 1
    else:
        logger.error('Unable to fetch revision code for node at {}'.format(node.addr))
    return nodes

def get_hardware_interface(*args, **kwargs):
    '''Returns the RotorHazard interface object.'''
    return RHInterface(*args, **kwargs)
