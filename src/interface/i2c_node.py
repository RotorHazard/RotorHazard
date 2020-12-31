'''RotorHazard I2C interface layer.'''
import logging
from monotonic import monotonic

from Node import Node
from RHInterface import READ_ADDRESS, MAX_RETRY_COUNT, validate_checksum, calculate_checksum

logger = logging.getLogger(__name__)


class I2CNode(Node):
    def __init__(self, index, addr, i2c_helper):
        Node.__init__(self)
        self.index = index
        self.i2c_addr = addr
        self.i2c_helper = i2c_helper

    def read_block(self, interface, command, size, max_retries=MAX_RETRY_COUNT):
        '''
        Read i2c data given command, and data size.
        '''
        self.inc_read_block_count(interface)
        success = False
        retry_count = 0
        data = None
        while success is False and retry_count <= max_retries:
            try:
                def _read():
                    self.io_request = monotonic()
                    _data = self.i2c_helper.i2c.read_i2c_block_data(self.i2c_addr, command, size + 1)
                    self.io_response = monotonic()
                    if validate_checksum(_data):
                        return _data
                    else:
                        return None
                data = self.i2c_helper.with_i2c(_read)
                if data:
                    success = True
                    data = data[:-1]
                else:
                    # self.log('Invalid Checksum ({0}): {1}'.format(retry_count, data))
                    retry_count = retry_count + 1
                    if retry_count <= max_retries:
                        if retry_count > 1:  # don't log the occasional single retry
                            interface.log('Retry (checksum) in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(self.i2c_addr, command, size, retry_count, self.i2c_helper.i2c_timestamp))
                    else:
                        interface.log('Retry (checksum) limit reached in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(self.i2c_addr, command, size, retry_count, self.i2c_helper.i2c_timestamp))
                    self.inc_read_error_count(interface)
            except IOError as err:
                interface.log('Read Error: ' + str(err))
                self.i2c_helper.i2c_end()
                retry_count = retry_count + 1
                if retry_count <= max_retries:
                    if retry_count > 1:  # don't log the occasional single retry
                        interface.log('Retry (IOError) in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(self.i2c_addr, command, size, retry_count, self.i2c_helper.i2c_timestamp))
                else:
                    interface.log('Retry (IOError) limit reached in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(self.i2c_addr, command, size, retry_count, self.i2c_helper.i2c_timestamp))
                self.inc_read_error_count(interface)
        return data

    def write_block(self, interface, command, data):
        '''
        Write i2c data given command, and data.
        '''
        interface.inc_intf_write_block_count()
        success = False
        retry_count = 0
        data_with_checksum = data
        if self.api_level <= 19:
            data_with_checksum.append(command)
        data_with_checksum.append(calculate_checksum(data_with_checksum))
        while success is False and retry_count <= MAX_RETRY_COUNT:
            try:
                def _write():
                    # self.io_request = monotonic()
                    self.i2c_helper.i2c.write_i2c_block_data(self.i2c_addr, command, data_with_checksum)
                    # self.io_response = monotonic()
                    return True
                success = self.i2c_helper.with_i2c(_write)
                if success is None:
                    success = False
            except IOError as err:
                interface.log('Write Error: ' + str(err))
                self.i2c_helper.i2c_end()
                retry_count = retry_count + 1
                if retry_count <= MAX_RETRY_COUNT:
                    interface.log('Retry (IOError) in write_block:  addr={0} cmd={1} data={2} retry={3} ts={4}'.format(self.i2c_addr, command, data, retry_count, self.i2c_helper.i2c_timestamp))
                else:
                    interface.log('Retry (IOError) limit reached in write_block:  addr={0} cmd={1} data={2} retry={3} ts={4}'.format(self.i2c_addr, command, data, retry_count, self.i2c_helper.i2c_timestamp))
                interface.inc_intf_write_error_count()
        return success

    def jump_to_bootloader(self, interface):
        pass


def discover(idxOffset, i2c_helper, *args, **kwargs):
    logger.info("Searching for I2C nodes...")
    nodes = []
    # Scans all i2c_addrs to populate nodes array
    i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
    for index, addr in enumerate(i2c_addrs):
        try:
            i2c_helper.i2c.read_i2c_block_data(addr, READ_ADDRESS, 1)
            logger.info("...I2C node {0} found at address {1}".format(index+idxOffset+1, addr))
            node = I2CNode(index+idxOffset, addr, i2c_helper) # New node instance
            nodes.append(node) # Add new node to RHInterface
        except IOError as err:
            logger.info("...No I2C node at address {0}".format(addr))
        i2c_helper.i2c_end()
        i2c_helper.i2c_sleep()
    return nodes
