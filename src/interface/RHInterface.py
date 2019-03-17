'''RotorHazard hardware interface layer.'''

import smbus # For i2c comms
import gevent # For threads and timing
from gevent.lock import BoundedSemaphore # To limit i2c calls

from Node import Node
from BaseHardwareInterface import BaseHardwareInterface

READ_ADDRESS = 0x00         # Gets i2c address of arduino (1 byte)
READ_FREQUENCY = 0x03       # Gets channel frequency (2 byte)
READ_LAP_STATS = 0x05
READ_FILTER_RATIO = 0x20    # node API_level>=10 uses 16-bit value
READ_REVISION_CODE = 0x22   # read NODE_API_LEVEL and verification value
READ_NODE_RSSI_PEAK = 0x23  # read 'nodeRssiPeak' value
READ_NODE_RSSI_NADIR = 0x24  # read 'nodeRssiNadir' value
READ_ENTER_AT_LEVEL = 0x31
READ_EXIT_AT_LEVEL = 0x32
READ_HISTORY_EXPIRE_DURATION = 0x35
READ_TIME_MILLIS = 0x33     # read current 'millis()' time value
READ_CATCH_HISTORY = 0x34   # get lap catch history data

WRITE_FREQUENCY = 0x51      # Sets frequency (2 byte)
WRITE_FILTER_RATIO = 0x70   # node API_level>=10 uses 16-bit value
WRITE_ENTER_AT_LEVEL = 0x71
WRITE_EXIT_AT_LEVEL = 0x72
WRITE_HISTORY_EXPIRE_DURATION = 0x73
MARK_START_TIME = 0x77      # mark base time for returned lap-ms-since-start values
FORCE_END_CROSSING = 0x78   # kill current crossing flag regardless of RSSI value

UPDATE_SLEEP = 0.1 # Main update loop delay

I2C_CHILL_TIME = 0.075 # Delay after i2c read/write
I2C_RETRY_COUNT = 5 # Limit of i2c retries

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value
MAX_RSSI_VALUE = 999             # reject RSSI readings above this value
CAP_ENTER_EXIT_AT_MILLIS = 3000  # number of ms for capture of enter/exit-at levels
ENTER_AT_PEAK_MARGIN = 5         # closest that captured enter-at level can be to node peak RSSI

def unpack_8(data):
    return data[0]

def pack_8(data):
    return [data]

def unpack_16(data):
    '''Returns the full variable from 2 bytes input.'''
    result = data[0]
    result = (result << 8) | data[1]
    return result

def pack_16(data):
    '''Returns a 2 part array from the full variable.'''
    part_a = (data >> 8)
    part_b = (data & 0xFF)
    return [part_a, part_b]

def unpack_32(data):
    '''Returns the full variable from 4 bytes input.'''
    result = data[0]
    result = (result << 8) | data[1]
    result = (result << 8) | data[2]
    result = (result << 8) | data[3]
    return result

def validate_checksum(data):
    '''Returns True if the checksum matches the data.'''
    if data is None:
        return False
    checksum = sum(data[:-1]) & 0xFF
    return checksum == data[-1]


class RHInterface(BaseHardwareInterface):
    def __init__(self):
        BaseHardwareInterface.__init__(self)
        self.update_thread = None # Thread for running the main update loop
        self.pass_record_callback = None # Function added in server.py
        self.hardware_log_callback = None # Function added in server.py
        self.new_enter_or_exit_at_callback = None # Function added in server.py
        self.node_crossing_callback = None # Function added in server.py

        self.i2c = smbus.SMBus(1) # Start i2c bus
        self.semaphore = BoundedSemaphore(1) # Limits i2c to 1 read/write at a time
        self.i2c_timestamp = -1
        self.i2c_lock = False # prevent calling i2c during race staging

        # Scans all i2c_addrs to populate nodes array
        self.nodes = [] # Array to hold each node object
        i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
        for index, addr in enumerate(i2c_addrs):
            try:
                self.i2c.read_i2c_block_data(addr, READ_ADDRESS, 1)
                print "Node {0} found at address {1}".format(index+1, addr)
                gevent.sleep(I2C_CHILL_TIME)
                node = Node() # New node instance
                node.i2c_addr = addr # Set current loop i2c_addr
                node.index = index
                self.nodes.append(node) # Add new node to RHInterface
            except IOError as err:
                print "No node at address {0}".format(addr)
            gevent.sleep(I2C_CHILL_TIME)

        for node in self.nodes:
            node.frequency = self.get_value_16(node, READ_FREQUENCY)
                   # read NODE_API_LEVEL and verification value:
            rev_val = self.get_value_16(node, READ_REVISION_CODE)
            if (rev_val >> 8) == 0x25:  # if verify passed (fn defined) then set API level
                node.api_level = rev_val & 0xFF
            else:
                node.api_level = 0  # if verify failed (fn not defined) then set API level to 0
            if node.api_level >= 10:
                node.api_valid_flag = True  # set flag for newer API functions supported
                node.node_peak_rssi = self.get_value_16(node, READ_NODE_RSSI_PEAK)
                if node.api_level >= 13:
                    node.node_nadir_rssi = self.get_value_16(node, READ_NODE_RSSI_NADIR)
                node.enter_at_level = self.get_value_16(node, READ_ENTER_AT_LEVEL)
                node.exit_at_level = self.get_value_16(node, READ_EXIT_AT_LEVEL)
                print "Node {0}: API_level={1}, Freq={2}, EnterAt={3}, ExitAt={4}".format(node.index+1, node.api_level, node.frequency, node.enter_at_level, node.exit_at_level)
            else:
                print "Node {0}: API_level={1}".format(node.index+1, node.api_level)
            if node.index == 0:
                if node.api_valid_flag:
                    self.filter_ratio = self.get_value_16(node, READ_FILTER_RATIO)
                else:
                    self.filter_ratio = 10
            else:
                self.set_filter_ratio(node.index, self.filter_ratio)


    #
    # Class Functions
    #

    def log(self, message):
        '''Hardware log of messages.'''
        if callable(self.hardware_log_callback):
            string = 'Interface: {0}'.format(message)
            self.hardware_log_callback(string)

    #
    # Update Loop
    #

    def start(self):
        if self.update_thread is None:
            self.log('Starting background thread.')
            self.update_thread = gevent.spawn(self.update_loop)

    def update_loop(self):
        try:
            while True:
                self.update()
                gevent.sleep(UPDATE_SLEEP)
        except KeyboardInterrupt:
            print "Update thread terminated by keyboard interrupt"

    def update(self):
        # stop asking for node updates during race staging
        # (clear i2c comms in prep for immediate start broadcast)
        if self.i2c_lock:
            return None

        upd_list = []  # list of nodes with new laps (node, new_lap_id, lap_time_ms)
        cross_list = []  # list of nodes with crossing-flag changes
        for node in self.nodes:
            if node.frequency:
                if node.api_valid_flag or node.api_level >= 5:
                    if node.api_level >= 13:
                        data = self.read_block(node.i2c_addr, READ_LAP_STATS, 20)
                    else:
                        data = self.read_block(node.i2c_addr, READ_LAP_STATS, 18)
                else:
                    data = self.read_block(node.i2c_addr, READ_LAP_STATS, 17)

                if data != None:
                    lap_id = data[0]
                    lap_time_ms = 0

                    rssi_val = unpack_16(data[5:])
                    if rssi_val >= MIN_RSSI_VALUE and rssi_val <= MAX_RSSI_VALUE:
                        node.current_rssi = rssi_val

                        if node.api_valid_flag:  # if newer API functions supported
                            ms_val = unpack_32(data[1:])
                            if ms_val < 0 or ms_val > 9999999:
                                ms_val = 0  # don't allow negative or too-large value
                            node.lap_ms_since_start = ms_val
                            node.node_peak_rssi = unpack_16(data[7:])
                            node.pass_peak_rssi = unpack_16(data[9:])
                            node.loop_time = unpack_32(data[11:])
                            if data[15]:
                                cross_flag = True
                            else:
                                cross_flag = False
                            if cross_flag != node.crossing_flag:  # if 'crossing' status changed
                                node.crossing_flag = cross_flag
                                if callable(self.node_crossing_callback):
                                    cross_list.append(node)
                            node.pass_nadir_rssi = unpack_16(data[16:])

                            if node.api_level >= 13:
                                node.node_nadir_rssi = unpack_16(data[18:])

                        else:  # if newer API functions not supported
                            lap_time_ms = unpack_32(data[1:])
                            node.pass_peak_rssi = unpack_16(data[11:])
                            node.loop_time = unpack_32(data[13:])

                        # if new lap detected for node then append item to updates list
                        if lap_id != node.last_lap_id:
                            upd_list.append((node, lap_id, lap_time_ms))

                        # check if capturing enter-at level for node
                        if node.cap_enter_at_flag:
                            node.cap_enter_at_total += node.current_rssi
                            node.cap_enter_at_count += 1
                            if self.milliseconds() >= node.cap_enter_at_millis:
                                node.enter_at_level = int(round(node.cap_enter_at_total / node.cap_enter_at_count))
                                node.cap_enter_at_flag = False
                                      # if too close node peak then set a bit below node-peak RSSI value:
                                if node.node_peak_rssi > 0 and node.node_peak_rssi - node.enter_at_level < ENTER_AT_PEAK_MARGIN:
                                    node.enter_at_level = node.node_peak_rssi - ENTER_AT_PEAK_MARGIN
                                self.transmit_enter_at_level(node, node.enter_at_level)
                                if callable(self.new_enter_or_exit_at_callback):
                                    self.new_enter_or_exit_at_callback(node, True)

                        # check if capturing exit-at level for node
                        if node.cap_exit_at_flag:
                            node.cap_exit_at_total += node.current_rssi
                            node.cap_exit_at_count += 1
                            if self.milliseconds() >= node.cap_exit_at_millis:
                                node.exit_at_level = int(round(node.cap_exit_at_total / node.cap_exit_at_count))
                                node.cap_exit_at_flag = False
                                self.transmit_exit_at_level(node, node.exit_at_level)
                                if callable(self.new_enter_or_exit_at_callback):
                                    self.new_enter_or_exit_at_callback(node, False)
                    else:
                        self.log('RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node.index+1))

        # process any nodes with crossing-flag changes
        if len(cross_list) > 0:
            for node in cross_list:
                self.node_crossing_callback(node)

        # process any nodes with new laps detected
        if len(upd_list) > 0:
            if len(upd_list) == 1:  # list contains single item
                item = upd_list[0]
                node = item[0]
                if node.last_lap_id != -1 and callable(self.pass_record_callback):
                    self.pass_record_callback(node, item[2])  # (node, lap_time_ms)
                node.last_lap_id = item[1]  # new_lap_id

            else:  # list contains multiple items; sort so processed in order by lap time
                upd_list.sort(key = lambda i: i[0].lap_ms_since_start)
                for item in upd_list:
                    node = item[0]
                    if node.last_lap_id != -1 and callable(self.pass_record_callback):
                        self.pass_record_callback(node, item[2])  # (node, lap_time_ms)
                    node.last_lap_id = item[1]  # new_lap_id


    #
    # I2C Common Functions
    #

    def i2c_sleep(self):
        if self.i2c_timestamp == -1:
            return
        time_passed = self.milliseconds() - self.i2c_timestamp
        time_remaining = (I2C_CHILL_TIME * 1000) - time_passed
        if (time_remaining > 0):
            # print("i2c sleep {0}".format(time_remaining))
            gevent.sleep(time_remaining / 1000.0)

    def read_block(self, addr, offset, size):
        '''Read i2c data given an address, code, and data size.'''
        if self.i2c_lock:
            self.log('Read prevented: I2C Locked')
            return None

        success = False
        retry_count = 0
        data = None
        while success is False and retry_count < I2C_RETRY_COUNT:
            try:
                with self.semaphore: # Wait if i2c comms is already in progress
                    self.i2c_sleep()
                    data = self.i2c.read_i2c_block_data(addr, offset, size + 1)
                    self.i2c_timestamp = self.milliseconds()
                    if validate_checksum(data):
                        success = True
                        data = data[:-1]
                    else:
                        # self.log('Invalid Checksum ({0}): {1}'.format(retry_count, data))
                        retry_count = retry_count + 1
                        if retry_count < I2C_RETRY_COUNT:
                            if retry_count > 1:  # don't log the occasional single retry
                                self.log('Retry (checksum) in read_block:  addr={0} offs={1} size={2} retry={3} ts={4}'.format(addr, offset, size, retry_count, self.i2c_timestamp))
                        else:
                            self.log('Retry (checksum) limit reached in read_block:  addr={0} offs={1} size={2} retry={3} ts={4}'.format(addr, offset, size, retry_count, self.i2c_timestamp))
            except IOError as err:
                self.log('Read Error: ' + str(err))
                self.i2c_timestamp = self.milliseconds()
                retry_count = retry_count + 1
                if retry_count < I2C_RETRY_COUNT:
                    if retry_count > 1:  # don't log the occasional single retry
                        self.log('Retry (IOError) in read_block:  addr={0} offs={1} size={2} retry={3} ts={4}'.format(addr, offset, size, retry_count, self.i2c_timestamp))
                else:
                    self.log('Retry (IOError) limit reached in read_block:  addr={0} offs={1} size={2} retry={3} ts={4}'.format(addr, offset, size, retry_count, self.i2c_timestamp))
        return data

    def write_block(self, addr, offset, data):
        '''Write i2c data given an address, code, and data.'''
        if self.i2c_lock:
            self.log('Write prevented: I2C Locked')
            return False

        success = False
        retry_count = 0
        data_with_checksum = data
        data_with_checksum.append(offset)
        data_with_checksum.append(sum(data_with_checksum) & 0xFF)
        while success is False and retry_count < I2C_RETRY_COUNT:
            try:
                with self.semaphore: # Wait if i2c comms is already in progress
                    self.i2c_sleep()
                    self.i2c.write_i2c_block_data(addr, offset, data_with_checksum)
                    self.i2c_timestamp = self.milliseconds()
                    success = True
            except IOError as err:
                self.log('Write Error: ' + str(err))
                self.i2c_timestamp = self.milliseconds()
                retry_count = retry_count + 1
                if retry_count < I2C_RETRY_COUNT:
                    self.log('Retry (IOError) in write_block:  addr={0} offs={1} data={2} retry={3} ts={4}'.format(addr, offset, data, retry_count, self.i2c_timestamp))
                else:
                    self.log('Retry (IOError) limit reached in write_block:  addr={0} offs={1} data={2} retry={3} ts={4}'.format(addr, offset, data, retry_count, self.i2c_timestamp))
        return success

    #
    # Internal helper functions for setting single values
    #

    def get_value_8(self, node, command):
        data = self.read_block(node.i2c_addr, command, 1)
        result = None
        if data != None:
            result = unpack_8(data)
        return result

    def get_value_16(self, node, command):
        data = self.read_block(node.i2c_addr, command, 2)
        result = None
        if data != None:
            result = unpack_16(data)
        return result

    def set_and_validate_value_8(self, node, write_command, read_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count < I2C_RETRY_COUNT:
            self.write_block(node.i2c_addr, write_command, pack_8(in_value))
            out_value = self.get_value_8(node, read_command)
            if out_value == in_value:
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0}): {1}/{2}/{3}'.format(retry_count, write_command, in_value, node))

        if out_value == None:
            out_value = in_value
        return out_value

    def set_and_validate_value_16(self, node, write_command, read_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count < I2C_RETRY_COUNT:
            self.write_block(node.i2c_addr, write_command, pack_16(in_value))
            out_value = self.get_value_16(node, read_command)
                   # confirm same value (also handle negative value)
            if out_value == in_value or out_value == in_value + (1 << 16):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0}): {1}/{2}/{3}'.format(retry_count, write_command, in_value, node))

        if out_value == None:
            out_value = in_value
        return out_value

    def set_value_8(self, node, write_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count < I2C_RETRY_COUNT:
            if self.write_block(node.i2c_addr, write_command, pack_8(in_value)):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0}): {1}/{2}/{3}'.format(retry_count, write_command, in_value, node))
        return success

    def broadcast_value_8(self, write_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count < I2C_RETRY_COUNT:
            if self.write_block(0x00, write_command, pack_8(in_value)):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0}): {1}/{2}/broadcast'.format(retry_count, write_command, in_value))
        return success

    #
    # External functions for setting data
    #

    def lock_i2c(self):
        self.i2c_lock = True

    def unlock_i2c(self):
        self.i2c_lock = False

    def set_frequency(self, node_index, frequency):
        node = self.nodes[node_index]
        node.debug_pass_count = 0  # reset debug pass count on frequency change
        if frequency:
            node.frequency = self.set_and_validate_value_16(node,
                WRITE_FREQUENCY,
                READ_FREQUENCY,
                frequency)
        else:  # if freq=0 (node disabled) then write default freq, but save 0 value
            self.set_and_validate_value_16(node,
                WRITE_FREQUENCY,
                READ_FREQUENCY,
                5800)
            node.frequency = 0

    def transmit_enter_at_level(self, node, level):
        return self.set_and_validate_value_16(node,
            WRITE_ENTER_AT_LEVEL,
            READ_ENTER_AT_LEVEL,
            level)

    def set_enter_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.api_valid_flag:
            node.enter_at_level = self.transmit_enter_at_level(node, level)

    def transmit_exit_at_level(self, node, level):
        return self.set_and_validate_value_16(node,
            WRITE_EXIT_AT_LEVEL,
            READ_EXIT_AT_LEVEL,
            level)

    def set_exit_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.api_valid_flag:
            node.exit_at_level = self.transmit_exit_at_level(node, level)

    def set_calibration_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def enable_calibration_mode(self):
        pass  # dummy function; no longer supported

    def set_calibration_offset_global(self, offset):
        return offset  # dummy function; no longer supported

    def set_trigger_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def set_filter_ratio(self, node_index, filter_ratio):
        node = self.nodes[node_index]
        if node.api_valid_flag:
            node.filter_ratio = self.set_and_validate_value_16(node,
                WRITE_FILTER_RATIO,
                READ_FILTER_RATIO,
                filter_ratio)

    def set_filter_ratio_global(self, filter_ratio):
        self.filter_ratio = filter_ratio
        for node in self.nodes:
            self.set_filter_ratio(node.index, filter_ratio)
        return self.filter_ratio

    def set_history_expire(self, node_index, history_expire_duration):
        node = self.nodes[node_index]
        if node.api_level >= 12:
            node.history_expire_duration = self.set_and_validate_value_16(node,
                WRITE_HISTORY_EXPIRE_DURATION,
                READ_HISTORY_EXPIRE_DURATION,
                history_expire_duration)

    def set_history_expire_global(self, history_expire_duration):
        for node in self.nodes:
            self.set_history_expire(node.index, history_expire_duration)

    def mark_start_time(self, node_index):
        node = self.nodes[node_index]
        if node.api_valid_flag:
            self.set_value_8(node, MARK_START_TIME, 0)

    def mark_start_time_global(self):
        self.unlock_i2c()
        bcast_flag = False
        for node in self.nodes:
            if self.nodes[0].api_level >= 15:
                if bcast_flag is False:
                    bcast_flag = True  # only send broadcast once
                    self.broadcast_value_8(MARK_START_TIME, 0)
            else:
                self.mark_start_time(node.index)  # if older API node

    def start_capture_enter_at_level(self, node_index):
        node = self.nodes[node_index]
        if node.cap_enter_at_flag is False and node.api_valid_flag:
            node.cap_enter_at_total = 0
            node.cap_enter_at_count = 0
                   # set end time for capture of RSSI level:
            node.cap_enter_at_millis = self.milliseconds() + CAP_ENTER_EXIT_AT_MILLIS
            node.cap_enter_at_flag = True
            return True
        return False

    def start_capture_exit_at_level(self, node_index):
        node = self.nodes[node_index]
        if node.cap_exit_at_flag is False and node.api_valid_flag:
            node.cap_exit_at_total = 0
            node.cap_exit_at_count = 0
                   # set end time for capture of RSSI level:
            node.cap_exit_at_millis = self.milliseconds() + CAP_ENTER_EXIT_AT_MILLIS
            node.cap_exit_at_flag = True
            return True
        return False

    def intf_simulate_lap(self, node_index, ms_val):
        node = self.nodes[node_index]
        node.lap_ms_since_start = ms_val
        self.pass_record_callback(node, 100)

    def get_catch_history(self, node_index):
        node = self.nodes[node_index]
        if node.api_level >= 12:
            data = self.read_block(node.i2c_addr, READ_CATCH_HISTORY, 8)
            return {
                'rssi_min': unpack_16(data[0:]),
                'rssi_max': unpack_16(data[2:]),
                'pass_ms': unpack_32(data[4:])
            }
        return None

    def force_end_crossing(self, node_index):
        node = self.nodes[node_index]
        if node.api_level >= 14:
            self.set_value_8(node, FORCE_END_CROSSING, 0)


def get_hardware_interface():
    '''Returns the RotorHazard interface object.'''
    return RHInterface()
