'''RotorHazard hardware interface layer.'''

import os
import gevent
import logging
from collections import deque
import json

import rh.interface.nodes as node_pkg
from rh.util.Plugins import Plugins
from . import pack_8, unpack_8, unpack_8_signed, pack_16, unpack_16
from .BaseHardwareInterface import BaseHardwareInterface
from .Node import Node, NodeManager
from rh.util import Averager


DEFAULT_WARN_LOOP_TIME = 1500
DEFAULT_RECORD_BUFFER_SIZE = 10000
JSONL_RECORD_FORMAT = 'jsonl'
BINARY_RECORD_FORMAT = 'bin'
DEFAULT_RECORD_FORMAT = JSONL_RECORD_FORMAT
STATS_WINDOW_SIZE = 100

READ_ADDRESS = 0x01         # Gets i2c address of arduino (1 byte)
READ_MODE = 0x02
READ_FREQUENCY = 0x03       # Gets channel frequency (2 byte)
READ_RSSI = 0x04
READ_LAP_STATS = 0x08
READ_ENTER_STATS = 0x09
READ_EXIT_STATS = 0x10
READ_RHFEAT_FLAGS = 0x11     # read feature flags value
READ_REVISION_CODE = 0x22    # read NODE_API_LEVEL and verification value
READ_RSSI_STATS = 0x23
READ_ANALYTICS = 0x24
READ_RSSI_HISTORY = 0x25
READ_SCAN_HISTORY = 0x26
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
WRITE_ENTER_AT_LEVEL = 0x71
WRITE_EXIT_AT_LEVEL = 0x72
WRITE_CURNODE_INDEX = 0x7A  # write index of current node for processor
SEND_STATUS_MESSAGE = 0x75  # send status message from server to node
FORCE_END_CROSSING = 0x78   # kill current crossing flag regardless of RSSI value
JUMP_TO_BOOTLOADER = 0x7E   # jump to bootloader for flash update

TIMER_MODE = 0
SCANNER_MODE = 1
RSSI_HISTORY_MODE = 2

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
    return unpack_8(data)


def unpack_time_since(node, cmd, data):
    ms_since = unpack_16(data)
    if ms_since >= 0xFFFF:
        logger.warning("Command {:#04x}: maximum lookback time exceeded on node {}".format(cmd, node))
    return ms_since


def has_data(data):
    return data is not None and len(data) > 0


class RHNodeManager(NodeManager):
    TYPE = "RH"
    MAX_RETRY_COUNT = 2

    def __init__(self):
        super().__init__()
        self.curr_multi_node_index = None
        self.api_level = 0
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
                                          if data is not None else None
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
            data = ((msgTypeVal & 0xFF) << 8) | (msgDataVal & 0xFF)
            self.set_value_16(SEND_STATUS_MESSAGE, data)
            return True
        except Exception:
            logger.exception('Error sending status message to {}'.format(self.addr))
        return False

    def discover_nodes(self, next_index):
        self.read_revision_code()
        if self.api_level >= 36:
            self.max_rssi_value = 255

            self.read_feature_flags()
            multi_count = self.read_multinode_count()
            if multi_count is None or multi_count > 32:
                logger.error('Bad READ_MULTINODE_COUNT value {} fetched from {}'.format(multi_count, self.addr))
                multi_count = 1
            elif multi_count == 0:
                logger.warning('Fetched READ_MULTINODE_COUNT value of zero from {} (no vrx modules detected)'.format(self.addr))

            if multi_count > 0:
                self.select = self._select_multi if multi_count > 1 else self._select_one

            info_strs = ["API level={}".format(self.api_level)]
            if self.read_firmware_version():
                info_strs.append("fw version={}".format(self.firmware_version_str))
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
        elif self.api_level > 0:
            logger.error('Unsupported API level {} - please upgrade'.format(self.api_level))
            return False
        else:
            logger.error('Unable to fetch revision code from {}'.format(self.addr))
            return False


class RHNode(Node):
    def __init__(self, index, multi_node_index, manager):
        super().__init__(index, multi_node_index, manager)
        self._loop_time_stats = Averager(STATS_WINDOW_SIZE)
        self._roundtrip_stats = Averager(STATS_WINDOW_SIZE)
        self.data_logger = None

    @Node.loop_time.setter  # type: ignore
    def loop_time(self, v):
        Node.loop_time.fset(self, v)
        self._loop_time_stats.append(v)

    def reset(self):
        super().reset()
        self._loop_time_stats.clear()

    def read_slot_index(self):
        # read node slot index (physical slot position of node on S32_BPill PCB)
        try:
            self.multi_node_slot_index = self.get_value_8(READ_NODE_SLOTIDX)
        except Exception:
            logger.exception('Error fetching READ_NODE_SLOTIDX from node {}'.format(self))
        return self.multi_node_slot_index

    def get_sent_time_ms(self):
        server_roundtrip_ms = self.io_response_ms - self.io_request_ms
        server_oneway_ms = round(server_roundtrip_ms / 2)
        sent_timestamp_ms = self.io_response_ms - server_oneway_ms
        return sent_timestamp_ms, server_roundtrip_ms

    def unpack_rssi(self, data):
        sent_timestamp_ms = None
        node_rssi = None
        lap_count = None
        is_crossing = None
        if has_data(data):
            sent_timestamp_ms, _ = self.get_sent_time_ms()
            node_rssi = unpack_rssi(self, data)
            if not self.is_valid_rssi(node_rssi):
                self.bad_rssi_count += 1
                # log the first ten, but then only 1 per 100 after that
                if self.bad_rssi_count <= 10 or self.bad_rssi_count % 100 == 0:
                    logger.warning("RSSI reading ({}) out of range on node {}; rejected; count={}".\
                             format(node_rssi, self, self.bad_rssi_count))
            lap_count = unpack_8(data[1:])
            is_crossing = (unpack_8(data[2:]) == 1)

            if self.data_logger is not None:
                self.data_logger.data_buffer.append((
                    READ_RSSI,
                    data,
                    (node_rssi, lap_count, is_crossing)
                ))
        return sent_timestamp_ms, node_rssi, lap_count, is_crossing

    def unpack_rssi_stats(self, data):
        peak_rssi = None
        nadir_rssi = None
        if has_data(data):
            rssi_val = unpack_rssi(self, data)
            if self.is_valid_rssi(rssi_val):
                peak_rssi = rssi_val
            rssi_val = unpack_rssi(self, data[1:])
            if self.is_valid_rssi(rssi_val):
                nadir_rssi = rssi_val

            if self.data_logger is not None:
                self.data_logger.data_buffer.append((
                    READ_RSSI_STATS,
                    data,
                    (peak_rssi, nadir_rssi)
                ))
        return peak_rssi, nadir_rssi

    def unpack_trigger_stats(self, cmd, data):
        trigger_count = None
        trigger_timestamp_ms = None
        trigger_rssi = None
        trigger_lifetime = None
        if has_data(data):
            sent_timestamp_ms, _ = self.get_sent_time_ms()

            trigger_count = unpack_8(data)
            ms_since_trigger = unpack_time_since(self, cmd, data[1:])
            trigger_timestamp_ms = sent_timestamp_ms - ms_since_trigger

            rssi_val = unpack_rssi(self, data[3:])
            if self.is_valid_rssi(rssi_val):
                trigger_rssi = rssi_val

            trigger_lifetime = unpack_8(data[4:])

            if self.data_logger is not None:
                self.data_logger.data_buffer.append((
                    cmd,
                    data,
                    (trigger_count, ms_since_trigger, trigger_rssi, trigger_lifetime)
                ))
        return trigger_count, trigger_timestamp_ms, trigger_rssi, trigger_lifetime

    def unpack_lap_stats(self, data):
        lap_count = None
        lap_timestamp_ms = None
        lap_peak_rssi = None
        lap_nadir_rssi = None
        if has_data(data):
            sent_timestamp_ms, server_roundtrip_ms = self.get_sent_time_ms()
            self._roundtrip_stats.append(server_roundtrip_ms)

            lap_count = unpack_8(data)
            ms_since_lap = unpack_time_since(self, READ_LAP_STATS, data[1:])
            lap_timestamp_ms = sent_timestamp_ms - ms_since_lap

            rssi_val = unpack_rssi(self, data[3:])
            if self.is_valid_rssi(rssi_val):
                lap_peak_rssi = rssi_val

            rssi_val = unpack_rssi(self, data[4:])
            if self.is_valid_rssi(rssi_val):
                lap_nadir_rssi = rssi_val

            if self.data_logger is not None:
                self.data_logger.data_buffer.append((
                    READ_LAP_STATS,
                    data,
                    (lap_count, ms_since_lap, lap_peak_rssi, lap_nadir_rssi)
                ))
        return lap_count, lap_timestamp_ms, lap_peak_rssi, lap_nadir_rssi

    def unpack_analytics(self, data):
        sent_timestamp_ms = None
        lifetime = None
        loop_time = None
        extremum_rssi = None
        extremum_timestamp_ms = None
        extremum_duration_ms = None
        if has_data(data):
            sent_timestamp_ms, _ = self.get_sent_time_ms()

            lifetime = unpack_8_signed(data)
            loop_time = unpack_16(data[1:])
            rssi_val = unpack_rssi(self, data[3:])
            if self.is_valid_rssi(rssi_val):
                extremum_rssi = rssi_val
                ms_since_first_time = unpack_time_since(self, READ_ANALYTICS, data[4:])  # ms *since* the first time
                extremum_timestamp_ms = sent_timestamp_ms - ms_since_first_time
                extremum_duration_ms = unpack_16(data[6:])
            elif rssi_val != 0:
                logger.warning("History RSSI reading ({}) out of range on node {}; rejected".format(rssi_val, self))

            if self.data_logger is not None:
                self.data_logger.data_buffer.append((
                    READ_ANALYTICS,
                    data,
                    (lifetime, loop_time, extremum_rssi, ms_since_first_time, extremum_duration_ms)
                ))
        return sent_timestamp_ms, lifetime, loop_time, extremum_rssi, extremum_timestamp_ms, extremum_duration_ms

    def poll_command(self, command, size):
        # as we are continually polling, no need to retry command
        return self.read_command(command, size, max_retries=0, log_level=logging.DEBUG)

    def summary_stats(self):
        msg = ["Node {}".format(self)]
        msg.append("\tComm round-trip (ms): {}".format(self._roundtrip_stats.formatted(1)))
        msg.append("\tLoop time (us): {}".format(self._loop_time_stats.formatted(0)))
        total_count = self.used_history_count + self.empty_history_count
        msg.append("\tRSSI history buffering utilisation: {:.2%}".format(self.used_history_count/total_count if total_count > 0 else 0))
        logger.debug('\n'.join(msg))


class RHInterface(BaseHardwareInterface):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update_count = 0
        self.warn_loop_time = kwargs['warn_loop_time'] if 'warn_loop_time' in kwargs else DEFAULT_WARN_LOOP_TIME
        self.FW_TEXT_BLOCK_SIZE = FW_TEXT_BLOCK_SIZE
        self.FW_VERSION_PREFIXSTR = FW_VERSION_PREFIXSTR
        self.FW_BUILDDATE_PREFIXSTR = FW_BUILDDATE_PREFIXSTR
        self.FW_BUILDTIME_PREFIXSTR = FW_BUILDTIME_PREFIXSTR
        self.FW_PROCTYPE_PREFIXSTR = FW_PROCTYPE_PREFIXSTR
        self.fwupd_serial_port = None  # serial port for in-app update of node firmware

        self.node_managers = Plugins(suffix='node')
        self.discover_nodes(*args, **kwargs)

        self.data_logger_buffer_size = int(os.environ.get('RH_RECORD_BUFFER', DEFAULT_RECORD_BUFFER_SIZE))
        self.data_logger_format = os.environ.get('RH_RECORD_FORMAT', DEFAULT_RECORD_FORMAT)

        for node in self.nodes:
            node.frequency = node.get_value_16(READ_FREQUENCY)
            if not node.frequency:
                raise RuntimeError('Unable to read frequency value from node {0}'.format(node))

            if node.manager.api_level >= 36:
                rssi_stats_data = node.read_command(READ_RSSI_STATS, 2)
                node.unpack_rssi_stats(rssi_stats_data)

                node.enter_at_level = self.get_value_rssi(node, READ_ENTER_AT_LEVEL)
                node.exit_at_level = self.get_value_rssi(node, READ_EXIT_AT_LEVEL)
                logger.debug("Node {}: Freq={}, EnterAt={}, ExitAt={}".format(\
                             node, node.frequency, node.enter_at_level, node.exit_at_level))
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

    def start(self):
        for node in self.nodes:
            if "RH_RECORD_NODE_{0}".format(node.index+1) in os.environ:
                self.start_data_logger(node.index)
        super().start()

    def stop(self):
        super().stop()
        for node in self.nodes:
            self.stop_data_logger(node.index)

    def start_data_logger(self, node_index):
        node = self.nodes[node_index]
        if node.data_logger is None:
            file_format = 'b' if self.data_logger_format == BINARY_RECORD_FORMAT else 't'
            f = open("node_data_{}.{}".format(node.index+1, self.data_logger_format), 'a'+file_format)
            logger.info("Data logging started for node {0} ({1})".format(node, f.name))
            f.data_buffer = deque([], self.data_logger_buffer_size)
            node.data_logger = f

    def stop_data_logger(self, node_index):
        node = self.nodes[node_index]
        f = node.data_logger
        if f is not None:
            self._flush_data_logger(f)
            f.close()
            logger.info("Stopped data logging for node {0} ({1})".format(node, f.name))
            node.data_logger = None

    def _flush_data_logger(self, f):
        buf = f.data_buffer
        if len(buf) == buf.maxlen:
            for r in buf:
                r_cmd, r_bytes, r_values = r
                if self.data_logger_format == BINARY_RECORD_FORMAT:
                    f.write(r_cmd)
                    f.write(len(r_bytes))
                    f.write(r_bytes)
                else:
                    f.write(json.dumps({'cmd': r_cmd, 'data': r_values})+'\n')
            buf.clear()

    #
    # Update Loop
    #

    def _update(self):
        node_sleep_interval = self.update_sleep/max(len(self.nodes), 1)
        if self.nodes:
            rssi_stats_node_idx = self.update_count % len(self.nodes)
            for node in self.nodes:
                if node.scan_enabled and callable(self.read_scan_history):
                    freqs, rssis = self.read_scan_history(node.index)
                    for freq, rssi in zip(freqs, rssis):
                        node.scan_data[freq] = rssi
                elif node.frequency:
                    rssi_data = node.poll_command(READ_RSSI, 3)
                    timestamp, rssi, pass_count, is_crossing = node.unpack_rssi(rssi_data)
                    if timestamp is not None and rssi is not None and pass_count is not None and is_crossing is not None:
                        has_new_lap, has_entered, has_exited = self.is_new_lap(node, timestamp, rssi, pass_count, is_crossing)
    
                        if has_entered:
                            cmd = READ_ENTER_STATS
                            crossing_data = node.poll_command(cmd, 5)
                            trigger_count, trigger_timestamp, trigger_rssi, trigger_lifetime = node.unpack_trigger_stats(cmd, crossing_data)
                            if trigger_count is not None and trigger_timestamp is not None and trigger_rssi is not None and trigger_lifetime is not None:
                                self.process_crossing(node, True, trigger_count, trigger_timestamp, trigger_rssi, trigger_lifetime)
    
                        if has_exited:
                            cmd = READ_EXIT_STATS
                            crossing_data = node.poll_command(cmd, 5)
                            trigger_count, trigger_timestamp, trigger_rssi, trigger_lifetime = node.unpack_trigger_stats(cmd, crossing_data)
                            if trigger_count is not None and trigger_timestamp is not None and trigger_rssi is not None and trigger_lifetime is not None:
                                self.process_crossing(node, False, trigger_count, trigger_timestamp, trigger_rssi, trigger_lifetime)
    
                        if has_new_lap:
                            lap_stats_data = node.poll_command(READ_LAP_STATS, 5)
                            lap_count, pass_timestamp, pass_peak_rssi, pass_nadir_rssi = node.unpack_lap_stats(lap_stats_data)
                            if lap_count is not None and pass_timestamp is not None:
                                self.process_lap_stats(node, lap_count, pass_timestamp, pass_peak_rssi, pass_nadir_rssi)

                    analytic_data = node.poll_command(READ_ANALYTICS, 8)
                    timestamp, lifetime, loop_time, extremum_rssi, extremum_timestamp, extremum_duration = node.unpack_analytics(analytic_data)
                    if timestamp is not None and lifetime is not None and loop_time is not None:
                        self.process_analytics(node, timestamp, lifetime, loop_time, extremum_rssi, extremum_timestamp, extremum_duration)

                    if node.index == rssi_stats_node_idx:
                        rssi_stats_data = node.poll_command(READ_RSSI_STATS, 2)
                        peak_rssi, nadir_rssi = node.unpack_rssi_stats(rssi_stats_data)
                        self.process_rssi_stats(node, peak_rssi, nadir_rssi)

                    self.process_capturing(node)

                    self._restore_lowered_thresholds(node)

                    if node.loop_time > self.warn_loop_time:
                        logger.warning("Abnormal loop time for node {}: {}us ({})".format(node, node.loop_time, node._loop_time_stats.formatted(0)))

                    if node.data_logger is not None:
                        self._flush_data_logger(node.data_logger)
                # end mode specific code
                gevent.sleep(node_sleep_interval)
            # end for each node
            self.update_count += 1
        else:
            gevent.sleep(node_sleep_interval)

    #
    # Internal helper functions for setting single values
    #

    def set_and_validate_value_rssi(self, node, write_command, read_command, in_value):
        return node.set_and_validate_value_8(write_command, read_command, in_value)

    def get_value_rssi(self, node, command):
        return node.get_value_8(command)

    def transmit_frequency(self, node, frequency):
        return node.set_and_validate_value_16(
            WRITE_FREQUENCY,
            READ_FREQUENCY,
            frequency)

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

    #
    # External functions for setting data
    #

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
            if scan_enabled:
                node.scan_enabled = scan_enabled
                # reset/clear data
                node.scan_data = {}
                self.set_mode(node_index, SCANNER_MODE)
            else:
                self.set_mode(node_index, TIMER_MODE)
                # reset/clear data
                node.scan_data = {}
                # restore original frequency
                original_freq = node.frequency
                node.frequency = 0
                self.set_frequency(node_index, original_freq)
                node.scan_enabled = scan_enabled

    def force_end_crossing(self, node_index):
        node = self.nodes[node_index]
        node.set_value_8(FORCE_END_CROSSING, 0)

    def jump_to_bootloader(self):
        for node_manager in self.node_managers:
            if (node_manager.rhfeature_flags & RHFEAT_JUMPTO_BOOTLDR) != 0 and hasattr(node_manager, 'jump_to_bootloader'):
                node_manager.jump_to_bootloader()
                return
        logger.info("Unable to find any nodes with jump-to-bootloader support")

    def read_scan_history(self, node_index):
        node = self.nodes[node_index]
        data = node.read_command(READ_SCAN_HISTORY, 9)
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
        return node.read_command(READ_RSSI_HISTORY, 16)

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
