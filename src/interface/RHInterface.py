'''RotorHazard hardware interface layer.'''

import os
import logging
import gevent # For threads and timing
from monotonic import monotonic # to capture read timing

from Plugins import Plugins
from BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory

READ_ADDRESS = 0x00         # Gets i2c address of arduino (1 byte)
READ_FREQUENCY = 0x03       # Gets channel frequency (2 byte)
READ_LAP_STATS = 0x05
READ_LAP_PASS_STATS = 0x0D
READ_LAP_EXTREMUMS = 0x0E
READ_RHFEAT_FLAGS = 0x11     # read feature flags value
# READ_FILTER_RATIO = 0x20    # node API_level>=10 uses 16-bit value
READ_REVISION_CODE = 0x22    # read NODE_API_LEVEL and verification value
READ_NODE_RSSI_PEAK = 0x23   # read 'nodeRssiPeak' value
READ_NODE_RSSI_NADIR = 0x24  # read 'nodeRssiNadir' value
READ_ENTER_AT_LEVEL = 0x31
READ_EXIT_AT_LEVEL = 0x32
READ_TIME_MILLIS = 0x33      # read current 'millis()' time value
READ_MULTINODE_COUNT = 0x39  # read # of nodes handled by processor
READ_CURNODE_INDEX = 0x3A    # read index of current node for processor
READ_NODE_SLOTIDX = 0x3C     # read node slot index (for multi-node setup)
READ_FW_VERSION = 0x3D       # read firmware version string
READ_FW_BUILDDATE = 0x3E     # read firmware build date string
READ_FW_BUILDTIME = 0x3F     # read firmware build time string

WRITE_FREQUENCY = 0x51       # Sets frequency (2 byte)
# WRITE_FILTER_RATIO = 0x70   # node API_level>=10 uses 16-bit value
WRITE_ENTER_AT_LEVEL = 0x71
WRITE_EXIT_AT_LEVEL = 0x72
WRITE_CURNODE_INDEX = 0x7A  # write index of current node for processor
FORCE_END_CROSSING = 0x78   # kill current crossing flag regardless of RSSI value
JUMP_TO_BOOTLOADER = 0x7E   # jump to bootloader for flash update

LAPSTATS_FLAG_CROSSING = 0x01  # crossing is in progress
LAPSTATS_FLAG_PEAK = 0x02      # reported extremum is peak

FW_TEXT_BLOCK_SIZE = 16     # length of data returned by 'READ_FW_...' fns

# prefix strings for finding text values in firmware '.bin' files
FW_VERSION_PREFIXSTR = "FIRMWARE_VERSION: "
FW_BUILDDATE_PREFIXSTR = "FIRMWARE_BUILDDATE: "
FW_BUILDTIME_PREFIXSTR = "FIRMWARE_BUILDTIME: "

# features flags for value returned by READ_RHFEAT_FLAGS command
RHFEAT_STM32_MODE = 0x0004      # STM 32-bit processor running multiple nodes
RHFEAT_JUMPTO_BOOTLDR = 0x0008  # JUMP_TO_BOOTLOADER command supported
RHFEAT_IAP_FIRMWARE = 0x0010    # in-application programming of firmware supported

UPDATE_SLEEP = float(os.environ.get('RH_UPDATE_INTERVAL', '0.1')) # Main update loop delay
MAX_RETRY_COUNT = 4 # Limit of I/O retries
MIN_RSSI_VALUE = 1               # reject RSSI readings below this value

logger = logging.getLogger(__name__)


def unpack_8(data):
    return data[0]

def pack_8(data):
    return [int(data & 0xFF)]

def unpack_16(data):
    '''Returns the full variable from 2 bytes input.'''
    result = data[0]
    result = (result << 8) | data[1]
    return result

def pack_16(data):
    '''Returns a 2 part array from the full variable.'''
    part_a = (data >> 8)
    part_b = (data & 0xFF)
    return [int(part_a), int(part_b)]

def unpack_32(data):
    '''Returns the full variable from 4 bytes input.'''
    result = data[0]
    result = (result << 8) | data[1]
    result = (result << 8) | data[2]
    result = (result << 8) | data[3]
    return result

def pack_32(data):
    '''Returns a 4 part array from the full variable.'''
    part_a = (data >> 24)
    part_b = (data >> 16) & 0xFF
    part_c = (data >> 8) & 0xFF
    part_d = (data & 0xFF)
    return [int(part_a), int(part_b), int(part_c), int(part_d)]


def calculate_checksum(data):
    checksum = sum(data) & 0xFF
    return checksum

def validate_checksum(data):
    '''Returns True if the checksum matches the data.'''
    if not data:
        return False
    checksum = calculate_checksum(data[:-1])
    return checksum == data[-1]

def unpack_rssi(node, data):
    if node.api_level >= 18:
        return unpack_8(data)
    else:
        return unpack_16(data) / 2


class RHInterface(BaseHardwareInterface):
    def __init__(self, *args, **kwargs):
        BaseHardwareInterface.__init__(self)
        self.FW_TEXT_BLOCK_SIZE = FW_TEXT_BLOCK_SIZE
        self.FW_VERSION_PREFIXSTR = FW_VERSION_PREFIXSTR
        self.FW_BUILDDATE_PREFIXSTR = FW_BUILDDATE_PREFIXSTR
        self.FW_BUILDTIME_PREFIXSTR = FW_BUILDTIME_PREFIXSTR
        self.update_thread = None      # Thread for running the main update loop
        self.fwupd_serial_obj = None   # serial object for in-app update of node firmware

        self.intf_read_block_count = 0  # number of blocks read by all nodes
        self.intf_read_error_count = 0  # number of read errors for all nodes
        self.intf_write_block_count = 0  # number of blocks write by all nodes
        self.intf_write_error_count = 0  # number of write errors for all nodes
        self.intf_error_report_limit = 0.0  # log if ratio of comm errors is larger

        self.nodes = Plugins(suffix='node')
        self.discover_nodes(*args, **kwargs)

        self.data_loggers = []
        for node in self.nodes:
            node.frequency = self.get_value_16(node, READ_FREQUENCY)
            if not node.frequency:
                raise RuntimeError('Unable to read frequency value from node {0}'.format(node.index+1))
            node.init()
            if node.api_level >= 10:
                node.node_peak_rssi = self.get_value_rssi(node, READ_NODE_RSSI_PEAK)
                if node.api_level >= 13:
                    node.node_nadir_rssi = self.get_value_rssi(node, READ_NODE_RSSI_NADIR)
                node.enter_at_level = self.get_value_rssi(node, READ_ENTER_AT_LEVEL)
                node.exit_at_level = self.get_value_rssi(node, READ_EXIT_AT_LEVEL)
                if node.multi_node_index < 0:  # (multi-nodes will always have default values)
                    logger.debug("Node {}: Freq={}, EnterAt={}, ExitAt={}".format(\
                                 node.index+1, node.frequency, node.enter_at_level, node.exit_at_level))

                if "RH_RECORD_NODE_{0}".format(node.index+1) in os.environ:
                    self.data_loggers.append(open("data_{0}.csv".format(node.index+1), 'w'))
                    logger.info("Data logging enabled for node {0}".format(node.index+1))
                else:
                    self.data_loggers.append(None)
            else:
                logger.warn("Node {} has obsolete API_level ({})".format(node.index+1, node.api_level))
            if node.api_level >= 32:
                flags_val = self.get_value_16(node, READ_RHFEAT_FLAGS)
                if flags_val:
                    node.rhfeature_flags = flags_val
                    # if first node that supports in-app fw update then save port name
                    if (not self.fwupd_serial_obj) and node.serial and \
                            (node.rhfeature_flags & (RHFEAT_STM32_MODE|RHFEAT_IAP_FIRMWARE)) != 0:
                        self.set_fwupd_serial_obj(node.serial)


    def discover_nodes(self, *args, **kwargs):
        self.nodes.discover(includeOffset=True, *args, **kwargs)


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

    def update_loop(self):
        while True:
            try:
                while True:
                    self.update()
                    gevent.sleep(UPDATE_SLEEP)
            except KeyboardInterrupt:
                logger.info("Update thread terminated by keyboard interrupt")
                raise
            except SystemExit:
                raise
            except Exception:
                logger.exception('Exception in RHInterface update_loop():')
                gevent.sleep(UPDATE_SLEEP*10)

    def update(self):
        upd_list = []  # list of nodes with new laps (node, new_lap_id, lap_timestamp)
        cross_list = []  # list of nodes with crossing-flag changes
        startThreshLowerNode = None
        for node in self.nodes:
            if node.frequency:
                if node.api_valid_flag or node.api_level >= 5:
                    if node.api_level >= 32:
                        data = node.read_block(self, READ_LAP_PASS_STATS, 8)
                        if data != None:
                            data.extend(node.read_block(self, READ_LAP_EXTREMUMS, 8))
                    elif node.api_level >= 21:
                        data = node.read_block(self, READ_LAP_STATS, 16)
                    elif node.api_level >= 18:
                        data = node.read_block(self, READ_LAP_STATS, 19)
                    elif node.api_level >= 17:
                        data = node.read_block(self, READ_LAP_STATS, 28)
                    elif node.api_level >= 13:
                        data = node.read_block(self, READ_LAP_STATS, 20)
                    else:
                        data = node.read_block(self, READ_LAP_STATS, 18)
                    server_roundtrip = node.io_response - node.io_request
                    server_oneway = server_roundtrip / 2
                    readtime = node.io_response - server_oneway
                else:
                    data = node.read_block(self, READ_LAP_STATS, 17)

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
                                            self.log('History peak RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node.index+1))
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
                                            self.log('History nadir RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node.index+1))
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
                            self.log('RSSI reading ({}) out of range on Node {}; rejected; count={}'.\
                                     format(rssi_val, node.index+1, node.bad_rssi_count))

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
    # Internal helper functions for setting single values
    #

    def get_value_8(self, node, command):
        data = node.read_block(self, command, 1)
        result = None
        if data != None:
            result = unpack_8(data)
        return result

    def get_value_16(self, node, command):
        data = node.read_block(self, command, 2)
        result = None
        if data != None:
            result = unpack_16(data)
        return result

    def get_value_32(self, node, command):
        data = node.read_block(self, command, 4)
        result = None
        if data != None:
            result = unpack_32(data)
        return result

    def set_and_validate_value_8(self, node, write_command, read_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            node.write_block(self, write_command, pack_8(in_value))
            out_value = self.get_value_8(node, read_command)
            if out_value == in_value:
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value 8v Not Set (retry={0}): cmd={1}, val={2}, node={3}'.\
                         format(retry_count, write_command, in_value, node.index+1))

        if out_value == None:
            out_value = in_value
        return out_value

    def set_and_validate_value_16(self, node, write_command, read_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            node.write_block(self, write_command, pack_16(in_value))
            out_value = self.get_value_16(node, read_command)
                   # confirm same value (also handle negative value)
            if out_value == in_value or out_value == in_value + (1 << 16):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value 16v Not Set (retry={0}): cmd={1}, val={2}, node={3}'.\
                         format(retry_count, write_command, in_value, node.index+1))

        if out_value == None:
            out_value = in_value
        return out_value

    def set_and_validate_value_32(self, node, write_command, read_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            node.write_block(self, write_command, pack_32(in_value))
            out_value = self.get_value_32(node, read_command)
                   # confirm same value (also handle negative value)
            if out_value == in_value or out_value == in_value + (1 << 32):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set 32v (retry={0}): cmd={1}, val={2}, node={3}'.\
                         format(retry_count, write_command, in_value, node.index+1))

        if out_value == None:
            out_value = in_value
        return out_value

    def set_value_8(self, node, write_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            if node.write_block(self, write_command, pack_8(in_value)):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value 8 Not Set (retry={0}): cmd={1}, val={2}, node={3}'.\
                         format(retry_count, write_command, in_value, node.index+1))
        return success

    def set_value_32(self, node, write_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            if node.write_block(self, write_command, pack_32(in_value)):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value 32 Not Set (retry={0}): cmd={1}, val={2}, node={3}'.\
                         format(retry_count, write_command, in_value, node.index+1))
        return success

    def set_and_validate_value_rssi(self, node, write_command, read_command, in_value):
        if node.api_level >= 18:
            return self.set_and_validate_value_8(node, write_command, read_command, in_value)
        else:
            return self.set_and_validate_value_16(node, write_command, read_command, in_value)

    def get_value_rssi(self, node, command):
        if node.api_level >= 18:
            return self.get_value_8(node, command)
        else:
            return self.get_value_16(node, command)

    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency):
        node = self.nodes[node_index]
        node.debug_pass_count = 0  # reset debug pass count on frequency change
        if frequency:
            node.frequency = self.set_and_validate_value_16(node,
                WRITE_FREQUENCY,
                READ_FREQUENCY,
                frequency)
        else:  # if freq=0 (node disabled) then write frequency value to power down rx module, but save 0 value
            self.set_and_validate_value_16(node,
                WRITE_FREQUENCY,
                READ_FREQUENCY,
                1111 if node.api_level >= 24 else 5800)
            node.frequency = 0

    def transmit_enter_at_level(self, node, level):
        return self.set_and_validate_value_rssi(node,
            WRITE_ENTER_AT_LEVEL,
            READ_ENTER_AT_LEVEL,
            level)

    def set_enter_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.api_valid_flag and node.is_valid_rssi(level):
            if self.transmit_enter_at_level(node, level):
                node.enter_at_level = level

    def transmit_exit_at_level(self, node, level):
        return self.set_and_validate_value_rssi(node,
            WRITE_EXIT_AT_LEVEL,
            READ_EXIT_AT_LEVEL,
            level)

    def set_exit_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.api_valid_flag and node.is_valid_rssi(level):
            if self.transmit_exit_at_level(node, level):
                node.exit_at_level = level

    def force_end_crossing(self, node_index):
        node = self.nodes[node_index]
        if node.api_level >= 14:
            self.set_value_8(node, FORCE_END_CROSSING, 0)

    def jump_to_bootloader(self):
        for node in self.nodes:
            if (node.rhfeature_flags & RHFEAT_JUMPTO_BOOTLDR) != 0:
                node.jump_to_bootloader(self)
                return
        self.log("Unable to find any nodes with jump-to-bootloader support")

    def set_fwupd_serial_obj(self, serial_obj):
        self.fwupd_serial_obj = serial_obj

    def set_mock_fwupd_serial_obj(self, port_name):
        serial_obj = type('', (), {})()  # empty base object
        def mock_no_op():
            pass
        serial_obj.name = port_name
        serial_obj.open = mock_no_op()
        serial_obj.close = mock_no_op()
        self.fwupd_serial_obj = serial_obj

    def get_fwupd_serial_name(self):
        return self.fwupd_serial_obj.name if self.fwupd_serial_obj else None

    def close_fwupd_serial_port(self):
        try:
            if self.fwupd_serial_obj:
                self.fwupd_serial_obj.close()
        except Exception as ex:
            self.log("Error closing FW node serial port: " + str(ex))

    def inc_intf_read_block_count(self):
        self.intf_read_block_count += 1

    def inc_intf_read_error_count(self):
        self.intf_read_error_count += 1

    def inc_intf_write_block_count(self):
        self.intf_write_block_count += 1

    def inc_intf_write_error_count(self):
        self.intf_write_error_count += 1

    def get_intf_total_error_count(self):
        return self.intf_read_error_count + self.intf_write_error_count

    # log comm errors if error percentage is >= this value
    def set_intf_error_report_percent_limit(self, percentVal):
        self.intf_error_report_limit = percentVal / 100;

    def get_intf_error_report_str(self, forceFlag=False):
        if self.intf_read_block_count <= 0:
            return None
        r_err_ratio = float(self.intf_read_error_count) / float(self.intf_read_block_count) \
                      if self.intf_read_error_count > 0 else 0
        w_err_ratio = float(self.intf_write_error_count) / float(self.intf_write_block_count) \
                      if self.intf_write_block_count > 0 and self.intf_write_error_count > 0 else 0
        if forceFlag or r_err_ratio > self.intf_error_report_limit or \
                                    w_err_ratio > self.intf_error_report_limit:
            retStr = "CommErrors:"
            if forceFlag or self.intf_write_error_count > 0:
                retStr += "Write:{0}/{1}({2:.2%}),".format(self.intf_write_error_count, \
                                self.intf_write_block_count, w_err_ratio)
            retStr += "Read:{0}/{1}({2:.2%})".format(self.intf_read_error_count, \
                                self.intf_read_block_count, r_err_ratio)
            for node in self.nodes:
                retStr += ", " + node.get_read_error_report_str()
            return retStr
        return None

def get_hardware_interface(*args, **kwargs):
    '''Returns the RotorHazard interface object.'''
    return RHInterface(*args, **kwargs)
