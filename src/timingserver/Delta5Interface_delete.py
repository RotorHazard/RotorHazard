import smbus
import gevent
from gevent.lock import BoundedSemaphore

from Node import Node

READ_ADDRESS = 0x00
READ_RSSI = 0x01
READ_FREQUENCY = 0x03
READ_TRIGGER_RSSI = 0x04
READ_LAP = 0x05
READ_TIMING_SERVER_MODE = 0x06

WRITE_TRIGGER_RSSI = 0x53
WRITE_FREQUENCY = 0x56
WRITE_TIMING_SERVER_MODE = 0x57

UPDATE_SLEEP = 0.1

I2C_CHILL_TIME = 0.05
I2C_RETRY_SLEEP = 0.05
I2C_RETRY_COUNT = 5

def unpack_16(data):
    result = data[0]
    result = (result << 8) | data[1]
    return result

def pack_16(data):
    part_a = (data >> 8)
    part_b = (data & 0xFF)
    return [part_a, part_b]

def unpack_32(data):
    result = data[0]
    result = (result << 8) | data[1]
    result = (result << 8) | data[2]
    result = (result << 8) | data[3]
    return result

def validate_checksum(data):
    if data == None:
        return False
    checksum = sum(data[:-1]) & 0xFF
    return checksum == data[-1]


class Delta5Interface:
    def __init__(self):
        self.update_thread = None
        self.pass_record_callback = None
        self.hardware_log_callback = None

        self.semaphore = BoundedSemaphore(1)

        # Start i2c bus
        self.i2c = smbus.SMBus(1)
        self.nodes = []

        i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22]

        for index, addr in enumerate(i2c_addrs):
            try:
                self.i2c.read_i2c_block_data(addr, READ_ADDRESS, 1)
                print ("Node FOUND at address {0}".format(addr))
                gevent.sleep(I2C_CHILL_TIME)
                node = Node()
                node.i2c_addr = addr
                node.index = index
                self.nodes.append(node)
                self.get_frequency_node(node)
                self.get_trigger_rssi_node(node)
                self.enable_timing_server_mode(node)
            except IOError as err:
                print ("No node at address {0}".format(addr))

            gevent.sleep(I2C_CHILL_TIME)

    def read_block(self, addr, offset, size):
        success = False
        retry_count = 0
        data = None
        while success == False and retry_count < I2C_RETRY_COUNT:
            try:
                with self.semaphore:
                    data = self.i2c.read_i2c_block_data(addr, offset, size + 1)
                    if validate_checksum(data):
                        success = True
                        gevent.sleep(I2C_CHILL_TIME)
                        data = data[:-1]
                    else:
                        self.log('Invalid Checksum ({0}): {1}'.format(retry_count, data))
                        retry_count = retry_count + 1
                        gevent.sleep(I2C_RETRY_SLEEP)
            except IOError as err:
                self.log(err)
                retry_count = retry_count + 1
                gevent.sleep(I2C_RETRY_SLEEP)
        return data

    def write_block(self, addr, offset, data):
        success = False
        retry_count = 0
        data_with_checksum = data
        data_with_checksum.append(sum(data) & 0xFF)
        while success == False and retry_count < I2C_RETRY_COUNT:
            try:
                with self.semaphore:
                    self.i2c.write_i2c_block_data(addr, offset, data_with_checksum)
                    success = True
                    gevent.sleep(I2C_CHILL_TIME)
            except IOError as err:
                self.log(err)
                retry_count = retry_count + 1
                gevent.sleep(I2C_RETRY_SLEEP)

    def update_loop(self):
        while True:
            self.update()
            gevent.sleep(UPDATE_SLEEP)

    def update(self):
        for node in self.nodes:
            data = self.read_block(node.i2c_addr, READ_LAP, 7)
            lap_id = data[0]
            ms_since_lap = unpack_32(data[1:])
            node.current_rssi = unpack_16(data[5:])

            if lap_id != node.last_lap_id:
                if (callable(self.pass_record_callback)):
                    self.pass_record_callback(node, ms_since_lap)
                node.last_lap_id = lap_id

    def start(self):
        if self.update_thread is None:
            self.log('starting background thread')
            self.update_thread = gevent.spawn(self.update_loop)

    def enable_timing_server_mode(self, node):
        success = False
        retry_count = 0

        while success == False and retry_count < I2C_RETRY_COUNT:
            self.write_block(node.i2c_addr, WRITE_TIMING_SERVER_MODE, [1])
            data = self.read_block(node.i2c_addr, READ_TIMING_SERVER_MODE, 1)
            if  data[0] == 1:
                print('Timing Server Mode Set')
                success = True
            else:
                retry_count = retry_count + 1
                print('Timing Server Mode Not Set ({0})'.format(retry_count))
                gevent.sleep(I2C_RETRY_SLEEP)

        return node.trigger_rssi


    def get_frequencies(self):
        for node in self.nodes:
            self.get_frequency_node(node)

    def get_frequency_node(self, node):
        data = self.read_block(node.i2c_addr, READ_FREQUENCY, 2)
        node.frequency = unpack_16(data)
        return node.frequency

    def set_frequency_index(self, node_index, frequency):
        success = False
        retry_count = 0

        node = self.nodes[node_index]
        while success == False and retry_count < I2C_RETRY_COUNT:
            self.write_block(node.i2c_addr, WRITE_FREQUENCY, pack_16(frequency))
            if self.get_frequency_node(node) == frequency:
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Frequency Not Set ({0})'.format(retry_count))

        return node.frequency

    def get_trigger_rssis(self):
        for node in self.nodes:
            self.get_trigger_rssi_node(node);

    def get_trigger_rssi_node(self, node):
        data = self.read_block(node.i2c_addr, READ_TRIGGER_RSSI, 2)
        node.trigger_rssi = unpack_16(data)
        return node.trigger_rssi

    def set_trigger_rssi_index(self, node_index, trigger_rssi):
        success = False
        retry_count = 0

        node = self.nodes[node_index]
        while success == False and retry_count < I2C_RETRY_COUNT:
            self.write_block(node.i2c_addr, WRITE_TRIGGER_RSSI, pack_16(trigger_rssi))
            if self.get_trigger_rssi_node(node) == trigger_rssi:
                success = True
            else:
                retry_count = retry_count + 1
                self.log('RSSI Not Set ({0})'.format(retry_count))

        return node.trigger_rssi

    def capture_trigger_rssi_index(self, node_index):
        node = self.nodes[node_index]
        return self.set_trigger_rssi_index(node_index, node.current_rssi)

    def log(self, message):
        if (callable(self.hardware_log_callback)):
            string = 'Delta5: {0}'.format(message)
            self.hardware_log_callback(string)

    def get_settings_json(self):
        settings = [node.get_settings_json() for node in self.nodes]
        return settings

    def get_heartbeat_json(self):
        return { 'current_rssi': [node.current_rssi for node in self.nodes]}

def get_hardware_interface():
    return Delta5Interface()
