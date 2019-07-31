'''RotorHazard hardware interface layer.'''

import serial # For serial comms
import gevent
from monotonic import monotonic

from Node import Node
from BaseRHInterface import BaseRHInterface, RETRY_COUNT, validate_checksum

BOOTLOADER_CHILL_TIME = 2 # Delay for USB to switch from bootloader to serial mode

class SerialRHInterface(BaseRHInterface):
    def __init__(self, *args, **kwargs):
        BaseRHInterface.__init__(self, *args, **kwargs)

    def discover_nodes(self, *args, **kwargs):
        config = kwargs['config']
        for index, comm in enumerate(config['SERIAL_PORTS']):
            node = Node()
            node.index = index
            node.serial = serial.Serial(port=comm, baudrate=115200, timeout=0.1)
            print("Node {0} found at port {1}".format(index+1, node.serial.name))
            self.nodes.append(node)

        gevent.sleep(BOOTLOADER_CHILL_TIME)


    #
    # Serial Common Functions
    #

    def read_block(self, node, command, size):
        '''
        Read data given node, command, and data size.
        If node is None then broadcast.
        '''
        success = False
        if node is None:
            raise IOError('Broadcast not yet implemented')
        ser = node.serial
        retry_count = 0
        data = None
        while success is False and retry_count < RETRY_COUNT:
            try:
                self.io_request = monotonic()
                ser.write(bytearray([command]))
                data = bytearray(ser.read(size + 1))
                self.io_response = monotonic()
                if validate_checksum(data):
                    success = True
                    data = data[:-1]
                else:
                    # self.log('Invalid Checksum ({0}): {1}'.format(retry_count, data))
                    retry_count = retry_count + 1
                    if retry_count < RETRY_COUNT:
                        if retry_count > 1:  # don't log the occasional single retry
                            self.log('Retry (checksum) in read_block:  port={0} cmd={1} size={2} retry={3}'.format(ser.port, command, size, retry_count))
                    else:
                        self.log('Retry (checksum) limit reached in read_block:  port={0} cmd={1} size={2} retry={3}'.format(ser.port, command, size, retry_count))
            except IOError as err:
                self.log('Read Error: ' + str(err))
                retry_count = retry_count + 1
                if retry_count < RETRY_COUNT:
                    if retry_count > 1:  # don't log the occasional single retry
                        self.log('Retry (IOError) in read_block:  port={0} cmd={1} size={2} retry={3}'.format(ser.port, command, size, retry_count))
                else:
                    self.log('Retry (IOError) limit reached in read_block:  port={0} cmd={1} size={2} retry={3}'.format(ser.port, command, size, retry_count))
        return data

    def write_block(self, node, command, data):
        '''
        Write data given node, command, and data.
        If node is None then broadcast.
        '''
        success = False
        if node is None:
            raise IOError('Broadcast not yet implemented')
        ser = node.serial
        retry_count = 0
        data_with_checksum = bytearray()
        data_with_checksum.append(command)
        data_with_checksum.extend(data)
        data_with_checksum.append(int(sum(data_with_checksum[1:]) & 0xFF))
        while success is False and retry_count < RETRY_COUNT:
            try:
                ser.write(data_with_checksum)
                success = True
            except IOError as err:
                self.log('Write Error: ' + str(err))
                retry_count = retry_count + 1
                if retry_count < RETRY_COUNT:
                    self.log('Retry (IOError) in write_block:  port={0} cmd={1} data={2} retry={3}'.format(ser.port, command, data, retry_count))
                else:
                    self.log('Retry (IOError) limit reached in write_block:  port={0} cmd={1} data={2} retry={3}'.format(ser.port, command, data, retry_count))
        return success


def get_hardware_interface(*args, **kwargs):
    '''Returns the RotorHazard interface object.'''
    return SerialRHInterface(*args, **kwargs)
