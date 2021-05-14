'''
Node class for the RotorHazard interface.
Command agnostic behaviour only.
'''

import logging
from monotonic import monotonic
import gevent.lock
from interface import pack_8, unpack_8, pack_16, unpack_16, pack_32, unpack_32, \
                        validate_checksum, calculate_checksum

MAX_RETRY_COUNT = 4 # Limit of I/O retries

logger = logging.getLogger(__name__)

class IndividualIOLine:
    def select(self, node):
        return True

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass

class SharedIOLine:
    REENTRANT_IO_LINE = IndividualIOLine()

    def __init__(self, select_write_cmd, select_read_cmd):
        self.select_write_cmd = select_write_cmd
        self.select_read_cmd = select_read_cmd
        self.lock = gevent.lock.RLock()
        self.curr_multi_node_index = None

    def select(self, node):
        if self.curr_multi_node_index != node.multi_node_index:
            curr_io_line = node.io_line
            node.io_line = SharedIOLine.REENTRANT_IO_LINE
            self.curr_multi_node_index = node.set_and_validate_value_8(self.select_write_cmd, self.select_read_cmd, node.multi_node_index)
            node.io_line = curr_io_line
        return self.curr_multi_node_index == node.multi_node_index

    def __enter__(self):
        self.lock.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.__exit__(exc_type, exc_value, traceback)

class Node:
    '''Node class represents the arduino/rx pair.'''
    def __init__(self, index, io_line=None):
        self.index = index
        # logical node index
        self.multi_node_index = None
        # physical slot position
        self.multi_node_slot_index = None
        self.io_line = io_line if io_line else IndividualIOLine()
        self.api_level = 0
        self.api_valid_flag = False
        self.rhfeature_flags = 0
        self.firmware_version_str = None
        self.firmware_proctype_str = None
        self.firmware_timestamp_str = None
        self.frequency = 0
        self.current_rssi = 0
        self.node_peak_rssi = 0
        self.node_nadir_rssi = 0
        self.pass_peak_rssi = 0
        self.pass_nadir_rssi = 0
        self.max_rssi_value = 255
        self.node_lap_id = -1
        self.current_pilot_id = 0
        self.first_cross_flag = False
        self.show_crossing_flag = False
        self.loop_time = 10 # microseconds
        self.crossing_flag = False
        self.pass_crossing_flag = False
        self.debug_pass_count = 0
        self.bad_rssi_count = 0

        self.enter_at_level = 0
        self.exit_at_level = 0

        self.start_thresh_lower_flag = False  # True while EnterAt/ExitAt lowered at start of race
        self.start_thresh_lower_time = 0      # time when EnterAt/ExitAt should be restored

        self.cap_enter_at_flag = False
        self.cap_enter_at_total = 0
        self.cap_enter_at_count = 0
        self.cap_enter_at_millis = 0
        self.cap_exit_at_flag = False
        self.cap_exit_at_total = 0
        self.cap_exit_at_count = 0
        self.cap_exit_at_millis = 0

        self.under_min_lap_count = 0

        self.history_values = []
        self.history_times = []

        self.scan_enabled = False
        self.scan_interval = 0 # scanning frequency interval
        self.min_scan_frequency = 0
        self.max_scan_frequency = 0
        self.max_scan_interval = 0
        self.min_scan_interval = 0
        self.scan_zoom = 0

        self.io_request = None # request time of last I/O read
        self.io_response = None # response time of last I/O read
        
        self.write_block_count = 0
        self.read_block_count = 0
        self.write_error_count = 0
        self.read_error_count = 0

    def close(self):
        pass

    def create_multi_node(self, index, multi_index):
        multi_node = self._create(index)
        multi_node.multi_node_index = multi_index
        multi_node.io_line = self.io_line
        multi_node.api_level = self.api_level
        multi_node.api_valid_flag = self.api_valid_flag
        multi_node.rhfeature_flags = self.rhfeature_flags
        multi_node.firmware_version_str = self.firmware_version_str
        multi_node.firmware_proctype_str = self.firmware_proctype_str
        multi_node.firmware_timestamp_str = self.firmware_timestamp_str
        return multi_node

    def is_multi_node(self):
        return self.multi_node_index is not None

    def set_scan_interval(self, minFreq, maxFreq, maxInterval, minInterval, zoom):
        if minFreq > 0 and minFreq <= maxFreq and minInterval > 0 and minInterval <= maxInterval and zoom > 0:
            self.scan_enabled = True
            self.min_scan_frequency = minFreq
            self.max_scan_frequency = maxFreq
            self.max_scan_interval = maxInterval
            self.min_scan_interval = minInterval
            self.scan_zoom = zoom
            self.scan_interval = maxInterval
        else:
            self.scan_enabled = False
            self.min_scan_frequency = 0
            self.max_scan_frequency = 0
            self.max_scan_interval = 0
            self.min_scan_interval = 0
            self.scan_zoom = 0
            self.scan_interval = 0

    def get_settings_json(self):
        return {
            'frequency': self.frequency,
            'current_rssi': self.current_rssi,
            'enter_at_level': self.enter_at_level,
            'exit_at_level': self.exit_at_level
        }

    def get_heartbeat_json(self):
        return {
            'current_rssi': self.current_rssi,
            'node_peak_rssi': self.node_peak_rssi,
            'pass_peak_rssi': self.pass_peak_rssi,
            'pass_nadir_rssi': self.pass_nadir_rssi
        }

    def is_valid_rssi(self, value):
        return value > 0 and value < self.max_rssi_value

    def inc_write_block_count(self):
        self.write_block_count += 1

    def inc_read_block_count(self):
        self.read_block_count += 1

    def inc_write_error_count(self):
        self.write_error_count += 1

    def inc_read_error_count(self):
        self.read_error_count += 1

    def get_read_error_report_str(self):
        return "Node{0}:{1}/{2}({3:.2%})".format(self.index+1, self.read_error_count, \
                self.read_block_count, (float(self.read_error_count) / float(self.read_block_count)))

    def read_block(self, command, size, max_retries=MAX_RETRY_COUNT):
        '''
        Read data given command, and data size.
        '''
        with self.io_line:  # only allow one greenlet at a time
            if self.io_line.select(self):
                return self._read_block(command, size, max_retries)

    def read_block_any(self, command, size, max_retries=MAX_RETRY_COUNT):
        '''
        Read data given command, and data size.
        '''
        with self.io_line:  # only allow one greenlet at a time
            return self._read_block(command, size, max_retries)

    def _read_block(self, command, size, max_retries=MAX_RETRY_COUNT):
        self.inc_read_block_count()
        success = False
        retry_count = 0
        data = None
        while success is False and retry_count <= max_retries:
            try:
                self.io_request = monotonic()
                data = self._read_command(command, size)
                self.io_response = monotonic()
                if validate_checksum(data):
                    if len(data) == size + 1:
                        data = data[:-1]
                        success = True
                    else:
                        retry_count += 1
                        if retry_count <= max_retries:
                            logger.warning('Retry (bad length {4}) in read_block:  addr={0} cmd={1:#02x} size={2} retry={3}'.format(self.addr, command, size, retry_count, len(data)-1))
                        else:
                            logger.warning('Retry (bad length {4}) limit reached in read_block:  addr={0} cmd={1:#02x} size={2} retry={3}'.format(self.addr, command, size, retry_count, len(data)-1))
                        self.inc_read_error_count()
                        gevent.sleep(0.025)
                else:
                    # logger.warning('Invalid Checksum ({0}): {1}'.format(retry_count, data))
                    retry_count += 1
                    if data and len(data) > 0:
                        if retry_count <= max_retries:
                            logger.warning('Retry (checksum) in read_block:  addr={0} cmd={1:#02x} size={2} retry={3}'.format(self.addr, command, size, retry_count))
                        else:
                            logger.warning('Retry (checksum) limit reached in read_block:  addr={0} cmd={1:#02x} size={2} retry={3}'.format(self.addr, command, size, retry_count))
                    else:
                        if retry_count <= max_retries:
                            logger.warning('Retry (no data) in read_block:  addr={0} cmd={1:#02x} size={2} retry={3}'.format(self.addr, command, size, retry_count))
                        else:
                            logger.warning('Retry (no data) limit reached in read_block:  addr={0} cmd={1:#02x} size={2} retry={3}'.format(self.addr, command, size, retry_count))
                    self.inc_read_error_count()
                    gevent.sleep(0.025)
            except IOError as err:
                logger.warning('Read Error: {}'.format(err))
                retry_count += 1
                if retry_count <= max_retries:
                    logger.warning('Retry (IOError) in read_block:  addr={0} cmd={1:#02x} size={2} retry={3}'.format(self.addr, command, size, retry_count))
                else:
                    logger.warning('Retry (IOError) limit reached in read_block:  addr={0} cmd={1:#02x} size={2} retry={3}'.format(self.addr, command, size, retry_count))
                self.inc_read_error_count()
                gevent.sleep(0.025)
        return data if success else None

    def write_block(self, command, data):
        '''
        Write data given command, and data.
        '''
        with self.io_line:  # only allow one greenlet at a time
            if self.io_line.select(self):
                return self._write_block(command, data)

    def write_block_any(self, command, data):
        '''
        Write data given command, and data.
        '''
        with self.io_line:  # only allow one greenlet at a time
            return self._write_block(command, data)

    def _write_block(self, command, data):
            self.inc_write_block_count()
            success = False
            retry_count = 0
            data_with_checksum = bytearray()
            data_with_checksum.extend(data)
            data_with_checksum.append(calculate_checksum(data_with_checksum))
            while success is False and retry_count <= MAX_RETRY_COUNT:
                try:
                    self._write_command(command, data_with_checksum)
                    success = True
                except IOError as err:
                    logger.warning('Write Error: {}'.format(err))
                    retry_count += 1
                    if retry_count <= MAX_RETRY_COUNT:
                        logger.warning('Retry (IOError) in write_block:  addr={0} cmd={1:#02x} data={2} retry={3}'.format(self.addr, command, data, retry_count))
                    else:
                        logger.warning('Retry (IOError) limit reached in write_block:  addr={0} cmd={1:#02x} data={2} retry={3}'.format(self.addr, command, data, retry_count))
                    self.inc_write_error_count()
                    gevent.sleep(0.025)
            return success

    def _get_value(self, command, read_func):
        with self.io_line:  # only allow one greenlet at a time
            if self.io_line.select(self):
                return read_func(command)

    def get_value_8(self, command):
        return self._get_value(command, self._get_value_8)

    def get_value_16(self, command):
        return self._get_value(command, self._get_value_16)

    def get_value_32(self, command):
        return self._get_value(command, self._get_value_32)

    def _get_value_8(self, command):
        data = self._read_block(command, 1)
        return unpack_8(data) if data is not None else None

    def _get_value_16(self, command):
        data = self._read_block(command, 2)
        return unpack_16(data) if data is not None else None

    def _get_value_32(self, command):
        data = self._read_block(command, 4)
        return unpack_32(data) if data is not None else None

    def _set_value(self, write_command, in_value, write_func, size):
        success = False
        retry_count = 0
        while success is False and retry_count <= MAX_RETRY_COUNT:
            with self.io_line:  # only allow one greenlet at a time
                if self.io_line.select(self):
                    if write_func(write_command, in_value):
                        success = True
                    else:
                        retry_count += 1
                        logger.info('{}bit value not set (retry={}): cmd={}, val={}, node={}'.\
                                 format(size, retry_count, write_command, in_value, self))
        return success

    def set_value_8(self, write_command, in_value):
        self._set_value(write_command, in_value, self._set_value_8, 8)

    def set_value_16(self, write_command, in_value):
        self._set_value(write_command, in_value, self._set_value_16, 16)

    def set_value_32(self, write_command, in_value):
        self._set_value(write_command, in_value, self._set_value_32, 32)

    def _set_value_8(self, command, val):
        self._write_block(command, pack_8(val))

    def _set_value_16(self, command, val):
        self._write_block(command, pack_16(val))

    def _set_value_32(self, command, val):
        self._write_block(command, pack_32(val))

    def _set_and_validate_value(self, write_command, read_command, in_value, write_func, read_func, size):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            with self.io_line:  # only allow one greenlet at a time
                if self.io_line.select(self):
                    write_func(write_command, in_value)
                    out_value = read_func(read_command)
                    if out_value == in_value:
                        success = True
                    else:
                        retry_count += 1
                        logger.info('{}bit value not set (retry={}): cmd={}, val={}, node={}'.\
                                 format(size, retry_count, write_command, in_value, self))
        return out_value if out_value is not None else in_value

    def set_and_validate_value_8(self, write_command, read_command, in_value):
        return self._set_and_validate_value(write_command, read_command, in_value, self._set_value_8, self._get_value_8, 8)

    def set_and_validate_value_16(self, write_command, read_command, in_value):
        return self._set_and_validate_value(write_command, read_command, in_value, self._set_value_16, self._get_value_16, 16)

    def set_and_validate_value_32(self, write_command, read_command, in_value):
        return self._set_and_validate_value(write_command, read_command, in_value, self._set_value_32, self._get_value_32, 32)

    def __str__(self):
        return str(self.index+1)
