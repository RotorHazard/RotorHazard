'''RotorHazard hardware interface layer.'''

import os
import smbus # For i2c comms
import io
import importlib
import gevent # For threads and timing
from gevent.lock import BoundedSemaphore # To limit i2c calls
from monotonic import monotonic # to capture read timing

from Node import Node
from BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory

READ_ADDRESS = 0x00         # Gets i2c address of arduino (1 byte)
READ_FREQUENCY = 0x03       # Gets channel frequency (2 byte)
READ_LAP_STATS = 0x05
# READ_FILTER_RATIO = 0x20    # node API_level>=10 uses 16-bit value
READ_REVISION_CODE = 0x22   # read NODE_API_LEVEL and verification value
READ_NODE_RSSI_PEAK = 0x23  # read 'nodeRssiPeak' value
READ_NODE_RSSI_NADIR = 0x24  # read 'nodeRssiNadir' value
READ_ENTER_AT_LEVEL = 0x31
READ_EXIT_AT_LEVEL = 0x32
READ_TIME_MILLIS = 0x33     # read current 'millis()' time value

WRITE_FREQUENCY = 0x51      # Sets frequency (2 byte)
# WRITE_FILTER_RATIO = 0x70   # node API_level>=10 uses 16-bit value
WRITE_ENTER_AT_LEVEL = 0x71
WRITE_EXIT_AT_LEVEL = 0x72
FORCE_END_CROSSING = 0x78   # kill current crossing flag regardless of RSSI value

UPDATE_SLEEP = float(os.environ.get('RH_UPDATE_INTERVAL', '0.1')) # Main update loop delay

I2C_CHILL_TIME = 0.075 # Delay after i2c read/write
I2C_RETRY_COUNT = 5 # Limit of i2c retries

MIN_RSSI_VALUE = 1               # reject RSSI readings below this value
CAP_ENTER_EXIT_AT_MILLIS = 3000  # number of ms for capture of enter/exit-at levels
ENTER_AT_PEAK_MARGIN = 5         # closest that captured enter-at level can be to node peak RSSI

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


def validate_checksum(data):
    '''Returns True if the checksum matches the data.'''
    if data is None:
        return False
    checksum = sum(data[:-1]) & 0xFF
    return checksum == data[-1]

def unpack_rssi(node, data):
    if node.api_level >= 18:
        return unpack_8(data)
    else:
        return unpack_16(data)


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
        self.i2c_request = None # request time of last I2C read
        self.i2c_response = None # response time of last I2C read

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

        self.data_loggers = []
        for node in self.nodes:
            node.frequency = self.get_value_16(node, READ_FREQUENCY)
                   # read NODE_API_LEVEL and verification value:
            rev_val = self.get_value_16(node, READ_REVISION_CODE)
            if (rev_val >> 8) == 0x25:  # if verify passed (fn defined) then set API level
                node.api_level = rev_val & 0xFF
            else:
                node.api_level = 0  # if verify failed (fn not defined) then set API level to 0
            node.init()
            if node.api_level >= 10:
                node.node_peak_rssi = self.get_value_rssi(node, READ_NODE_RSSI_PEAK)
                if node.api_level >= 13:
                    node.node_nadir_rssi = self.get_value_rssi(node, READ_NODE_RSSI_NADIR)
                node.enter_at_level = self.get_value_rssi(node, READ_ENTER_AT_LEVEL)
                node.exit_at_level = self.get_value_rssi(node, READ_EXIT_AT_LEVEL)
                print "Node {0}: API_level={1}, Freq={2}, EnterAt={3}, ExitAt={4}".format(node.index+1, node.api_level, node.frequency, node.enter_at_level, node.exit_at_level)

                if "RH_RECORD_NODE_{0}".format(node.index+1) in os.environ:
                    self.data_loggers.append(open("data_{0}.csv".format(node.index+1), 'w'))
                    print "Data logging enabled for node {0}".format(node.index+1)
                else:
                    self.data_loggers.append(None)
            else:
                print "Node {0}: API_level={1}".format(node.index+1, node.api_level)

        # Core temperature
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            self.core_temp = float(f.read())/1000

        self.environmental_data_update_tracker = 0

        # Scan for INA219 devices
        self.ina219_devices = []
        self.ina219_data = []
        supported_ina219_addrs = [0x40, 0x41, 0x44, 0x45]
        try:
            self.ina219Class = getattr(importlib.import_module('ina219'), 'INA219')
            for index, addr in enumerate(supported_ina219_addrs):
                try:
                    device = self.ina219Class(0.1, address=addr)
                    device.configure()
                    data = {
                        'voltage': device.voltage(),
                        'current': device.current(),
                        'power': device.power()
                    }
                    device.sleep()
                    print "INA219 found at address {0}".format(addr)
                    gevent.sleep(I2C_CHILL_TIME)
                    self.ina219_devices.append(device)
                    self.ina219_data.append(data)
                except IOError as err:
                    print "No INA219 at address {0}".format(addr)
                gevent.sleep(I2C_CHILL_TIME)
        except ImportError:
            self.ina219Class = None

        # Scan for BME280 devices
        self.bme280_addrs = []
        self.bme280_data = []
        supported_bme280_addrs = [0x76, 0x77]
        try:
            self.bme280SampleMethod = getattr(importlib.import_module('bme280'), 'sample')
            for index, addr in enumerate(supported_bme280_addrs):
                try:
                    data = self.bme280SampleMethod(self.i2c, addr)
                    print "BME280 found at address {0}".format(addr)
                    gevent.sleep(I2C_CHILL_TIME)
                    self.bme280_addrs.append(addr)
                    self.bme280_data.append(data)
                except IOError as err:
                    print "No BME280 at address {0}".format(addr)
                gevent.sleep(I2C_CHILL_TIME)
        except ImportError:
            self.bme280SampleMethod = None


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
        upd_list = []  # list of nodes with new laps (node, new_lap_id, lap_timestamp)
        cross_list = []  # list of nodes with crossing-flag changes
        for node in self.nodes:
            if node.frequency:
                if node.api_valid_flag or node.api_level >= 5:
                    if node.api_level >= 18:
                        data = self.read_block(node.i2c_addr, READ_LAP_STATS, 19)
                        server_roundtrip = self.i2c_response - self.i2c_request
                        server_oneway = server_roundtrip / 2
                        readtime = self.i2c_response - server_oneway

                    elif node.api_level >= 17:
                        data = self.read_block(node.i2c_addr, READ_LAP_STATS, 28)
                        server_roundtrip = self.i2c_response - self.i2c_request
                        server_oneway = server_roundtrip / 2
                        readtime = self.i2c_response - server_oneway

                    elif node.api_level >= 13:
                        data = self.read_block(node.i2c_addr, READ_LAP_STATS, 20)
                    else:
                        data = self.read_block(node.i2c_addr, READ_LAP_STATS, 18)
                else:
                    data = self.read_block(node.i2c_addr, READ_LAP_STATS, 17)

                if data != None:
                    lap_id = data[0]

                    if node.api_level >= 18:
                        offset_rssi = 3
                        offset_nodePeakRssi = 4
                        offset_passPeakRssi = 5
                        offset_loopTime = 6
                        offset_crossing = 8
                        offset_passNadirRssi = 9
                        offset_nodeNadirRssi = 10
                        offset_peakRssi = 11
                        offset_peakFirstTime = 12
                        offset_peakLastTime = 14
                        offset_nadirRssi = 16
                        offset_nadirTime = 17
                    else:
                        offset_rssi = 5
                        offset_nodePeakRssi = 7
                        offset_passPeakRssi = 9
                        offset_loopTime = 11
                        offset_crossing = 15
                        offset_passNadirRssi = 16
                        offset_nodeNadirRssi = 18
                        offset_peakRssi = 20
                        offset_peakTime = 22
                        offset_nadirRssi = 24
                        offset_nadirTime = 26

                    rssi_val = unpack_rssi(node, data[offset_rssi:])
                    if node.is_valid_rssi(rssi_val):
                        node.current_rssi = rssi_val

                        cross_flag = None
                        pn_history = None
                        if node.api_valid_flag:  # if newer API functions supported
                            if node.api_level >= 18:
                                ms_val = unpack_16(data[1:])
                                pn_history = PeakNadirHistory()
                                pn_history.peakRssi = unpack_rssi(node, data[offset_peakRssi:])
                                pn_history.peakFirstTime = unpack_16(data[offset_peakFirstTime:]) # ms *since* the first peak time
                                pn_history.peakLastTime = unpack_16(data[offset_peakLastTime:])   # ms *since* the last peak time
                                pn_history.nadirRssi = unpack_rssi(node, data[offset_nadirRssi:])
                                pn_history.nadirTime = unpack_16(data[offset_nadirTime:])
                            else:
                                ms_val = unpack_32(data[1:])

                            node.node_peak_rssi = unpack_rssi(node, data[offset_nodePeakRssi:])
                            node.pass_peak_rssi = unpack_rssi(node, data[offset_passPeakRssi:])
                            node.loop_time = unpack_16(data[offset_loopTime:])
                            if data[offset_crossing]:
                                cross_flag = True
                            else:
                                cross_flag = False
                            node.pass_nadir_rssi = unpack_rssi(node, data[offset_passNadirRssi:])

                            if node.api_level >= 13:
                                node.node_nadir_rssi = unpack_rssi(node, data[offset_nodeNadirRssi:])

                            if node.api_level >= 18:
                                data_logger = self.data_loggers[node.index]
                                if data_logger:
                                    data_logger.write("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14}\n".format(readtime,lap_id, int(ms_val), node.current_rssi, node.node_peak_rssi, node.pass_peak_rssi, node.loop_time, 'T' if cross_flag else 'F', node.pass_nadir_rssi, node.node_nadir_rssi, peakRssi, peakFirstTime, peakLastTime, nadirRssi, nadirTime))

                        else:  # if newer API functions not supported
                            ms_val = unpack_32(data[1:])
                            node.pass_peak_rssi = unpack_rssi(node, data[11:])
                            node.loop_time = unpack_32(data[13:])

                        self.process_lap_stats(node, readtime, lap_id, ms_val, cross_flag, pn_history, cross_list, upd_list)

                    else:
                        self.log('RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node.index+1))

        # process any nodes with crossing-flag changes
        self.process_crossings(cross_list)

        # process any nodes with new laps detected
        self.process_updates(upd_list)


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
        success = False
        retry_count = 0
        data = None
        while success is False and retry_count < I2C_RETRY_COUNT:
            try:
                with self.semaphore: # Wait if i2c comms is already in progress
                    self.i2c_sleep()
                    self.i2c_request = monotonic()
                    data = self.i2c.read_i2c_block_data(addr, offset, size + 1)
                    self.i2c_response = monotonic()
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
        success = False
        retry_count = 0
        data_with_checksum = data
        data_with_checksum.append(offset)
        data_with_checksum.append(int(sum(data_with_checksum) & 0xFF))
        while success is False and retry_count < I2C_RETRY_COUNT:
            try:
                with self.semaphore: # Wait if i2c comms is already in progress
                    self.i2c_sleep()
                    # self.i2c_request = monotonic()
                    self.i2c.write_i2c_block_data(addr, offset, data_with_checksum)
                    # self.i2c_response = monotonic()
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

    def get_value_32(self, node, command):
        data = self.read_block(node.i2c_addr, command, 4)
        result = None
        if data != None:
            result = unpack_32(data)
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

    def set_and_validate_value_32(self, node, write_command, read_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count < I2C_RETRY_COUNT:
            self.write_block(node.i2c_addr, write_command, pack_32(in_value))
            out_value = self.get_value_32(node, read_command)
                   # confirm same value (also handle negative value)
            if out_value == in_value or out_value == in_value + (1 << 32):
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

    def set_value_32(self, node, write_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count < I2C_RETRY_COUNT:
            if self.write_block(node.i2c_addr, write_command, pack_32(in_value)):
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

    def broadcast_value_32(self, write_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count < I2C_RETRY_COUNT:
            if self.write_block(0x00, write_command, pack_32(in_value)):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0}): {1}/{2}/broadcast'.format(retry_count, write_command, in_value))
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
        else:  # if freq=0 (node disabled) then write default freq, but save 0 value
            self.set_and_validate_value_16(node,
                WRITE_FREQUENCY,
                READ_FREQUENCY,
                5800)
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

    def set_calibration_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def enable_calibration_mode(self):
        pass  # dummy function; no longer supported

    def set_calibration_offset_global(self, offset):
        return offset  # dummy function; no longer supported

    def set_trigger_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def mark_start_time(self, node_index, start_time):
        node = self.nodes[node_index]
        if node.api_valid_flag:
            self.set_value_32(node, MARK_START_TIME, start_time)

    def mark_start_time_global(self, pi_time):
        bcast_flag = False
        start_time = int(round(pi_time * 1000)) # convert to ms
        for node in self.nodes:
            if self.nodes[0].api_level >= 15:
                if bcast_flag is False:
                    bcast_flag = True  # only send broadcast once
                    self.broadcast_value_32(MARK_START_TIME, start_time)
            else:
                self.mark_start_time(node.index, start_time)  # if older API node

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

    def force_end_crossing(self, node_index):
        node = self.nodes[node_index]
        if node.api_level >= 14:
            self.set_value_8(node, FORCE_END_CROSSING, 0)

    def update_environmental_data(self):
        '''Updates environmental data.'''
        self.environmental_data_update_tracker += 1

        if self.ina219Class and (self.environmental_data_update_tracker % 2) == 0:
            for index, device in enumerate(self.ina219_devices):
                try:
                    with self.semaphore:
                        self.i2c_sleep()
                        device = self.ina219_devices[index]
                        device.wake()
                        data = {
                            'voltage': device.voltage(),
                            'current': device.current(),
                            'power': device.power()/1000.0
                        }
                        device.sleep()
                        self.ina219_data[index] = data
                        self.i2c_timestamp = self.milliseconds()
                except IOError as err:
                    self.log('INA219 Read Error: ' + str(err))
                    self.i2c_timestamp = self.milliseconds()

        if self.bme280SampleMethod and (self.environmental_data_update_tracker % 2) == 1:
            for index, addr in enumerate(self.bme280_addrs):
                try:
                    with self.semaphore:
                        self.i2c_sleep()
                        data = self.bme280SampleMethod(self.i2c, addr)
                        self.bme280_data[index] = data
                        self.i2c_timestamp = self.milliseconds()
                except IOError as err:
                    self.log('BME280 Read Error: ' + str(err))
                    self.i2c_timestamp = self.milliseconds()

        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            self.core_temp = float(f.read())/1000

def get_hardware_interface():
    '''Returns the RotorHazard interface object.'''
    return RHInterface()
