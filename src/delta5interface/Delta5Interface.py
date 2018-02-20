'''Delta 5 hardware interface layer.'''

import smbus # For i2c comms
import gevent # For threads and timing
from gevent.lock import BoundedSemaphore # To limit i2c calls

from Node import Node
from BaseHardwareInterface import BaseHardwareInterface

READ_ADDRESS = 0x00 # Gets i2c address of arduino (1 byte)
READ_FREQUENCY = 0x03 # Gets channel frequency (2 byte)
READ_LAP_STATS = 0x05
READ_CALIBRATION_THRESHOLD = 0x15
READ_CALIBRATION_MODE = 0x16
READ_CALIBRATION_OFFSET = 0x17
READ_TRIGGER_THRESHOLD = 0x18
READ_FILTER_RATIO = 0x19

WRITE_FREQUENCY = 0x51 # Sets frequency (2 byte)
WRITE_CALIBRATION_THRESHOLD = 0x65
WRITE_CALIBRATION_MODE = 0x66
WRITE_CALIBRATION_OFFSET = 0x67
WRITE_TRIGGER_THRESHOLD = 0x68
WRITE_FILTER_RATIO = 0x69

UPDATE_SLEEP = 0.1 # Main update loop delay

I2C_CHILL_TIME = 0.075 # Delay after i2c read/write
I2C_RETRY_COUNT = 5 # Limit of i2c retries

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


class Delta5Interface(BaseHardwareInterface):
    def __init__(self):
        BaseHardwareInterface.__init__(self)
        self.update_thread = None # Thread for running the main update loop
        self.pass_record_callback = None # Function added in server.py
        self.hardware_log_callback = None # Function added in server.py

        self.i2c = smbus.SMBus(1) # Start i2c bus
        self.semaphore = BoundedSemaphore(1) # Limits i2c to 1 read/write at a time
        self.i2c_timestamp = -1

        # Scans all i2c_addrs to populate nodes array
        self.nodes = [] # Array to hold each node object
        i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
        for index, addr in enumerate(i2c_addrs):
            try:
                self.i2c.read_i2c_block_data(addr, READ_ADDRESS, 1)
                print "Node FOUND at address {0}".format(addr)
                gevent.sleep(I2C_CHILL_TIME)
                node = Node() # New node instance
                node.i2c_addr = addr # Set current loop i2c_addr
                node.index = index
                self.nodes.append(node) # Add new node to Delta5Interface
            except IOError as err:
                print "No node at address {0}".format(addr)
            gevent.sleep(I2C_CHILL_TIME)

        for node in self.nodes:
            node.frequency = self.get_value_16(node, READ_FREQUENCY)
            if node.index == 0:
                self.calibration_threshold = self.get_value_16(node,
                    READ_CALIBRATION_THRESHOLD)
                self.calibration_offset = self.get_value_16(node,
                    READ_CALIBRATION_OFFSET)
                self.trigger_threshold = self.get_value_16(node,
                    READ_TRIGGER_THRESHOLD)
                self.filter_ratio = self.get_value_8(node,
                    READ_FILTER_RATIO)
            else:
                self.set_calibration_threshold(node.index, self.calibration_threshold)
                self.set_calibration_offset(node.index, self.calibration_offset)
                self.set_trigger_threshold(node.index, self.trigger_threshold)


    #
    # Class Functions
    #

    def log(self, message):
        '''Hardware log of messages.'''
        if callable(self.hardware_log_callback):
            string = 'Delta 5 Log: {0}'.format(message)
            self.hardware_log_callback(string)

    #
    # Update Loop
    #

    def start(self):
        if self.update_thread is None:
            self.log('Starting background thread.')
            self.update_thread = gevent.spawn(self.update_loop)

    def update_loop(self):
        while True:
            self.update()
            gevent.sleep(UPDATE_SLEEP)

    def update(self):
        for node in self.nodes:
            data = self.read_block(node.i2c_addr, READ_LAP_STATS, 17)
            if data != None:
                lap_id = data[0]
                ms_since_lap = unpack_32(data[1:])
                node.current_rssi = unpack_16(data[5:])
                node.trigger_rssi = unpack_16(data[7:])
                node.peak_rssi_raw = unpack_16(data[9:])
                node.peak_rssi = unpack_16(data[11:])
                node.loop_time = unpack_32(data[13:])

                if lap_id != node.last_lap_id:
                    if node.last_lap_id != -1 and callable(self.pass_record_callback):
                        self.pass_record_callback(node, ms_since_lap)
                    node.last_lap_id = lap_id

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
                    data = self.i2c.read_i2c_block_data(addr, offset, size + 1)
                    self.i2c_timestamp = self.milliseconds()
                    if validate_checksum(data):
                        success = True
                        data = data[:-1]
                    else:
                        # self.log('Invalid Checksum ({0}): {1}'.format(retry_count, data))
                        retry_count = retry_count + 1
            except IOError as err:
                self.log(err)
                self.i2c_timestamp = self.milliseconds()
                retry_count = retry_count + 1
        return data

    def write_block(self, addr, offset, data):
        '''Write i2c data given an address, code, and data.'''
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
                self.log(err)
                self.i2c_timestamp = self.milliseconds()
                retry_count = retry_count + 1
        return success

    #
    # Internal helper fucntions for setting single values
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
                self.log('Value Not Set ({0})'.format(retry_count))

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
            if out_value == in_value:
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0})'.format(retry_count))

        if out_value == None:
            out_value = in_value
        return out_value

    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency):
        node = self.nodes[node_index]
        node.frequency = self.set_and_validate_value_16(node,
            WRITE_FREQUENCY,
            READ_FREQUENCY,
            frequency)

    def set_calibration_threshold(self, node_index, threshold):
        node = self.nodes[node_index]
        node.calibration_threshold = self.set_and_validate_value_16(node,
            WRITE_CALIBRATION_THRESHOLD,
            READ_CALIBRATION_THRESHOLD,
            threshold)

    def set_calibration_threshold_global(self, threshold):
        self.calibration_threshold = threshold
        for node in self.nodes:
            self.set_calibration_threshold(node.index, threshold)
        return self.calibration_threshold

    def set_calibration_mode(self, node_index, calibration_mode):
        node = self.nodes[node_index]
        self.set_and_validate_value_8(node,
            WRITE_CALIBRATION_MODE,
            READ_CALIBRATION_MODE,
            calibration_mode)

    def enable_calibration_mode(self):
        for node in self.nodes:
            self.set_calibration_mode(node.index, True);

    def set_calibration_offset(self, node_index, offset):
        node = self.nodes[node_index]
        node.calibration_offset = self.set_and_validate_value_16(node,
            WRITE_CALIBRATION_OFFSET,
            READ_CALIBRATION_OFFSET,
            offset)

    def set_calibration_offset_global(self, offset):
        self.calibration_offset = offset
        for node in self.nodes:
            self.set_calibration_offset(node.index, offset)
        return self.calibration_offset

    def set_trigger_threshold(self, node_index, threshold):
        node = self.nodes[node_index]
        node.trigger_threshold = self.set_and_validate_value_16(node,
            WRITE_TRIGGER_THRESHOLD,
            READ_TRIGGER_THRESHOLD,
            threshold)

    def set_trigger_threshold_global(self, threshold):
        self.trigger_threshold = threshold
        for node in self.nodes:
            self.set_trigger_threshold(node.index, threshold)
        return self.trigger_threshold

    def set_filter_ratio(self, node_index, filter_ration):
        node = self.nodes[node_index]
        node.filter_ration = self.set_and_validate_value_8(node,
            WRITE_FILTER_RATIO,
            READ_FILTER_RATIO,
            filter_ration)

    def set_filter_ratio_global(self, filter_ratio):
        self.filter_ratio = filter_ratio
        for node in self.nodes:
            self.set_filter_ratio(node.index, filter_ratio)
        return self.filter_ratio

    def intf_simulate_lap(self, node_index):
        node = self.nodes[node_index]
        node.current_rssi = 11
        node.trigger_rssi = 22
        node.peak_rssi_raw = 33
        node.peak_rssi = 44
        node.loop_time = 55
        self.pass_record_callback(node, 100)

def get_hardware_interface():
    '''Returns the delta 5 interface object.'''
    return Delta5Interface()
