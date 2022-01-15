'''
Node class for the RotorHazard interface.
Command agnostic behaviour only.
'''

import logging
from time import perf_counter
import gevent.lock
from interface import pack_8, unpack_8, pack_16, unpack_16, pack_32, unpack_32, \
                        calculate_checksum, RssiHistory

MAX_RETRY_COUNT = 4 # Limit of I/O retries

logger = logging.getLogger(__name__)


class CommandsWithRetry:
    def __init__(self, manager):
        self.manager = manager

        self.io_request = None # request time of last I/O read
        self.io_response = None # response time of last I/O read

        self.write_command_count = 0
        self.read_command_count = 0
        self.write_error_count = 0
        self.read_error_count = 0

    def read_command(self, command, size, max_retries=MAX_RETRY_COUNT, log_level=logging.WARNING):
        self.read_command_count += 1
        success = False
        retry_count = 0

        def log_io_error(msg):
            nonlocal retry_count
            if retry_count < max_retries:
                logger.debug('Retry ({4}) in read_command: addr={0} cmd={1:#04x} size={2} retry={3}'.format(self.addr, command, size, retry_count, msg))
            else:
                logger.log(log_level, 'Retry ({4}) limit reached in read_command: addr={0} cmd={1:#04x} size={2} retry={3}'.format(self.addr, command, size, retry_count, msg))
            retry_count += 1
            self.read_error_count += 1
            gevent.sleep(0.025)

        data = None
        while success is False and retry_count <= max_retries:
            try:
                self.io_response = None
                self.io_request = perf_counter()
                data = self.manager._read_command(command, size)
                self.io_response = perf_counter()
                if data and len(data) == size + 1:
                    # validate checksum
                    expected_checksum = calculate_checksum(data[:-1])
                    actual_checksum = data[-1]
                    if actual_checksum == expected_checksum:
                        data = data[:-1]
                        success = True
                    else:
                        log_io_error("checksum was {} expected {}".format(actual_checksum, expected_checksum))
                else:
                    log_io_error("bad length {}".format(len(data)) if data else "no data")
            except IOError as err:
                log_io_error(err)
        return data if success else None

    def write_command(self, command, data, max_retries=MAX_RETRY_COUNT, log_level=logging.WARNING):
        self.write_command_count += 1
        success = False
        retry_count = 0

        def log_io_error(msg):
            nonlocal retry_count
            if retry_count <= max_retries:
                logger.debug('Retry ({4}) in write_command: addr={0} cmd={1:#04x} data={2} retry={3}'.format(self.addr, command, data, retry_count, msg))
            else:
                logger.log(log_level, 'Retry ({4}) limit reached in write_command: addr={0} cmd={1:#04x} data={2} retry={3}'.format(self.addr, command, data, retry_count, msg))
            retry_count += 1
            self.write_error_count += 1
            gevent.sleep(0.025)

        data_with_checksum = bytearray()
        data_with_checksum.extend(data)
        data_with_checksum.append(calculate_checksum(data_with_checksum))
        while success is False and retry_count <= max_retries:
            try:
                self.manager._write_command(command, data_with_checksum)
                success = True
            except IOError as err:
                log_io_error(err)
        return success

    def get_value_8(self, command, max_retries=MAX_RETRY_COUNT):
        data = self.read_command(command, 1, max_retries)
        return unpack_8(data) if data is not None else None

    def get_value_16(self, command, max_retries=MAX_RETRY_COUNT):
        data = self.read_command(command, 2, max_retries)
        return unpack_16(data) if data is not None else None

    def get_value_32(self, command):
        data = self.read_command(command, 4)
        return unpack_32(data) if data is not None else None

    def set_value_8(self, command, val):
        self.write_command(command, pack_8(val))

    def set_value_16(self, command, val):
        self.write_command(command, pack_16(val))

    def set_value_32(self, command, val):
        self.write_command(command, pack_32(val))

    def set_and_validate_value(self, write_func, write_command, read_func, read_command, in_value, size, max_retries=MAX_RETRY_COUNT):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= max_retries:
            write_func(write_command, in_value)
            out_value = read_func(read_command, size)
            if out_value == in_value:
                success = True
            else:
                retry_count += 1
                logger.info('Value not set (retry={0}): cmd={1:#04x}, set={2}, get={3}, node={4}'.\
                         format(retry_count, write_command, in_value, out_value, self))
        return out_value if out_value is not None else in_value

    def set_and_validate_value_8(self, write_command, read_command, val):
        return self.set_and_validate_value(self.set_value_8, write_command, self.get_value_8, read_command, val, 1)

    def set_and_validate_value_16(self, write_command, read_command, val):
        return self.set_and_validate_value(self.set_value_16, write_command, self.get_value_16, read_command, val, 2)

    def set_and_validate_value_32(self, write_command, read_command, val):
        return self.set_and_validate_value(self.set_value_32, write_command, self.get_value_32, read_command, val, 4)


class NodeManager(CommandsWithRetry):
    def __init__(self):
        super().__init__(manager=self)
        self.nodes = []
        self.lock = gevent.lock.RLock()

    def is_multi_node(self):
        return len(self.nodes) > 1

    def add_node(self, index):
        node = self._create_node(index, len(self.nodes))
        self.nodes.append(node)
        return node

    def _create_node(self, index, multi_node_index):
        return Node(index, multi_node_index, self)

    def read_command(self, command, size, max_retries=MAX_RETRY_COUNT, log_level=logging.WARNING):
        '''
        Read data given command, and data size.
        '''
        with self:  # only allow one greenlet at a time
            return super().read_command(command, size, max_retries, log_level)

    def write_command(self, command, data, max_retries=MAX_RETRY_COUNT, log_level=logging.WARNING):
        '''
        Write data given command, and data.
        '''
        with self:  # only allow one greenlet at a time
            return super().write_command(command, data, max_retries, log_level)

    def set_and_validate_value(self, write_func, write_command, read_func, read_command, val, size, max_retries=MAX_RETRY_COUNT):
        with self:  # only allow one greenlet at a time
            return super().set_and_validate_value(write_func, write_command, read_func, read_command, val, size, max_retries)

    def select(self, node):
        return True

    def close(self):
        pass

    def get_disabled_frequency(self):
        return 5800

    def __enter__(self):
        self.lock.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.__exit__(exc_type, exc_value, traceback)


class Node(CommandsWithRetry):
    '''Node class represents the arduino/rx pair.'''
    def __init__(self, index, multi_node_index, manager):
        super().__init__(manager=manager)
        # logical node index within an interface
        self.index = index
        # logical node index within a manager
        self.multi_node_index = multi_node_index
        # physical slot position
        self.multi_node_slot_index = None
        self.addr = "{}#{}".format(self.manager.addr, self.multi_node_index)

        self.frequency = 0
        self.bandChannel = None
        self.current_rssi = 0
        self.node_peak_rssi = 0
        self.node_nadir_rssi = manager.max_rssi_value
        self.pass_peak_rssi = 0
        self.pass_nadir_rssi = manager.max_rssi_value
        self.pass_count = None
        self.current_pilot_id = 0
        self.first_cross_flag = False
        self.show_crossing_flag = False
        self._loop_time = 0 # microseconds
        self.crossing_flag = False
        self.pass_crossing_flag = False
        self.enter_at_timestamp = 0
        self.exit_at_timestamp = 0
        self.debug_pass_count = 0
        self.bad_rssi_count = 0

        self.enter_at_level = 0
        self.exit_at_level = 0
        self.ai_calibrate = False
        self.calibrate = True

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

        self.pass_history = []
        self.history = RssiHistory()
        self.used_history_count = 0
        self.empty_history_count = 0

        self.scan_enabled = False
        self.scan_data = {}

    @property
    def loop_time(self):
        return self._loop_time

    @loop_time.setter
    def loop_time(self, v):
        self._loop_time = v

    def reset(self):
        self.pass_history = []
        self.history = RssiHistory() # clear race history
        self.used_history_count = 0
        self.empty_history_count = 0
        self.pass_count = None
        self.under_min_lap_count = 0
        self._loop_time = 0 # microseconds

    def is_valid_rssi(self, value):
        return value > 0 and value < self.manager.max_rssi_value

    def get_read_error_report_str(self):
        return "Node {0}: {1}/{2} ({3:.2%})".format(self, self.read_error_count, \
                self.read_command_count, (float(self.read_error_count) / float(self.read_command_count)))

    def read_command(self, command, size, max_retries=MAX_RETRY_COUNT, log_level=logging.WARNING):
        '''
        Read data given command, and data size.
        '''
        with self.manager:  # only allow one greenlet at a time
            if self.manager.select(self):
                return super().read_command(command, size, max_retries, log_level)

    def write_command(self, command, data, max_retries=MAX_RETRY_COUNT, log_level=logging.WARNING):
        '''
        Write data given command, and data.
        '''
        with self.manager:  # only allow one greenlet at a time
            if self.manager.select(self):
                return super().write_command(command, data, max_retries, log_level)

    def set_and_validate_value(self, write_func, write_command, read_func, read_command, val, size, max_retries=MAX_RETRY_COUNT):
        with self.manager:  # only allow one greenlet at a time
            if self.manager.select(self):
                return super().set_and_validate_value(write_func, write_command, read_func, read_command, val, size, max_retries)

    def summary_stats(self):
        pass

    def __str__(self):
        return "{}@{}".format(self.index+1, self.addr)
