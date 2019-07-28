'''RotorHazard hardware interface layer.'''

import smbus # For i2c comms
from gevent.lock import BoundedSemaphore # To limit i2c calls
from monotonic import monotonic

from Node import Node
from BaseRHInterface import BaseRHInterface, RETRY_COUNT, validate_checksum

I2C_CHILL_TIME = 0.075 # Delay after i2c read/write

class RHInterface(BaseRHInterface):
    def __init__(self, *args, **kwargs):
        BaseRHInterface.__init__(self, *args, **kwargs)

        self.discover_sensors(config=kwargs['config'].get('SENSORS', {}), i2c_helper=self)


    def discover_nodes(self, *args, **kwargs):
        self.i2c = smbus.SMBus(1) # Start i2c bus
        self.semaphore = BoundedSemaphore(1) # Limits i2c to 1 read/write at a time
        self.i2c_timestamp = -1

        # Scans all i2c_addrs to populate nodes array
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

    def read_block(self, node, command, size):
        '''
        Read i2c data given node, command, and data size.
        If node is None then broadcast.
        '''
        success = False
        addr = node.i2c_addr if node else 0x00
        retry_count = 0
        data = None
        while success is False and retry_count < RETRY_COUNT:
            try:
                with self.semaphore: # Wait if i2c comms is already in progress
                    self.i2c_sleep()
                    self.io_request = monotonic()
                    data = self.i2c.read_i2c_block_data(addr, command, size + 1)
                    self.io_response = monotonic()
                    self.i2c_timestamp = self.milliseconds()
                    if validate_checksum(data):
                        success = True
                        data = data[:-1]
                    else:
                        # self.log('Invalid Checksum ({0}): {1}'.format(retry_count, data))
                        retry_count = retry_count + 1
                        if retry_count < RETRY_COUNT:
                            if retry_count > 1:  # don't log the occasional single retry
                                self.log('Retry (checksum) in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(addr, command, size, retry_count, self.i2c_timestamp))
                        else:
                            self.log('Retry (checksum) limit reached in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(addr, command, size, retry_count, self.i2c_timestamp))
            except IOError as err:
                self.log('Read Error: ' + str(err))
                self.i2c_timestamp = self.milliseconds()
                retry_count = retry_count + 1
                if retry_count < RETRY_COUNT:
                    if retry_count > 1:  # don't log the occasional single retry
                        self.log('Retry (IOError) in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(addr, command, size, retry_count, self.i2c_timestamp))
                else:
                    self.log('Retry (IOError) limit reached in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(addr, command, size, retry_count, self.i2c_timestamp))
        return data

    def write_block(self, node, command, data):
        '''
        Write i2c data given node, command, and data.
        If node is None then broadcast.
        '''
        success = False
        addr = node.i2c_addr if node else 0x00
        retry_count = 0
        data_with_checksum = data
        data_with_checksum.append(command)
        data_with_checksum.append(int(sum(data_with_checksum) & 0xFF))
        while success is False and retry_count < RETRY_COUNT:
            try:
                with self.semaphore: # Wait if i2c comms is already in progress
                    self.i2c_sleep()
                    # self.io_request = monotonic()
                    self.i2c.write_i2c_block_data(addr, command, data_with_checksum)
                    # self.io_response = monotonic()
                    self.i2c_timestamp = self.milliseconds()
                    success = True
            except IOError as err:
                self.log('Write Error: ' + str(err))
                self.i2c_timestamp = self.milliseconds()
                retry_count = retry_count + 1
                if retry_count < RETRY_COUNT:
                    self.log('Retry (IOError) in write_block:  addr={0} cmd={1} data={2} retry={3} ts={4}'.format(addr, command, data, retry_count, self.i2c_timestamp))
                else:
                    self.log('Retry (IOError) limit reached in write_block:  addr={0} cmd={1} data={2} retry={3} ts={4}'.format(addr, command, data, retry_count, self.i2c_timestamp))
        return success

    def with_i2c(self, callback):
        val = None
        if callable(callback):
            try:
                with self.semaphore:
                    self.i2c_sleep()
                    val = callback()
                    self.i2c_timestamp = self.milliseconds()
            except IOError as err:
                self.log('I2C error: '+str(err))
                self.i2c_timestamp = self.milliseconds()
        return val


def get_hardware_interface(*args, **kwargs):
    '''Returns the RotorHazard interface object.'''
    return RHInterface(*args, **kwargs)
