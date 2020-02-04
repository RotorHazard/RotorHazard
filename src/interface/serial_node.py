'''RotorHazard hardware interface layer.'''

import serial # For serial comms
import gevent
from monotonic import monotonic

from Node import Node
from RHInterface import RETRY_COUNT, validate_checksum, calculate_checksum

BOOTLOADER_CHILL_TIME = 2 # Delay for USB to switch from bootloader to serial mode

class SerialNode(Node):
    def __init__(self, index, port):
        Node.__init__(self)
        self.index = index
        self.serial = serial.Serial(port=port, baudrate=115200, timeout=0.1)


    #
    # Serial Common Functions
    #

    def read_block(self, interface, command, size):
        '''
        Read serial data given command, and data size.
        '''
        success = False
        retry_count = 0
        data = None
        while success is False and retry_count < RETRY_COUNT:
            try:
                self.io_request = monotonic()
                self.serial.write(bytearray([command]))
                data = bytearray(self.serial.read(size + 1))
                self.io_response = monotonic()
                if validate_checksum(data):
                    success = True
                    data = data[:-1]
                else:
                    # self.log('Invalid Checksum ({0}): {1}'.format(retry_count, data))
                    gevent.sleep(0.1)
                    retry_count = retry_count + 1
                    if retry_count < RETRY_COUNT:
                        if retry_count > 1:  # don't log the occasional single retry
                            interface.log('Retry (checksum) in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                    else:
                        interface.log('Retry (checksum) limit reached in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
            except IOError as err:
                interface.log('Read Error: ' + str(err))
                gevent.sleep(0.1)
                retry_count = retry_count + 1
                if retry_count < RETRY_COUNT:
                    if retry_count > 1:  # don't log the occasional single retry
                        interface.log('Retry (IOError) in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                else:
                    interface.log('Retry (IOError) limit reached in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
        return data

    def write_block(self, interface, command, data):
        '''
        Write serial data given command, and data.
        '''
        success = False
        retry_count = 0
        data_with_checksum = bytearray()
        data_with_checksum.append(command)
        data_with_checksum.extend(data)
        data_with_checksum.append(calculate_checksum(data_with_checksum[1:]))
        while success is False and retry_count < RETRY_COUNT:
            try:
                self.serial.write(data_with_checksum)
                success = True
            except IOError as err:
                interface.log('Write Error: ' + str(err))
                retry_count = retry_count + 1
                if retry_count < RETRY_COUNT:
                    interface.log('Retry (IOError) in write_block:  port={0} cmd={1} data={2} retry={3}'.format(self.serial.port, command, data, retry_count))
                else:
                    interface.log('Retry (IOError) limit reached in write_block:  port={0} cmd={1} data={2} retry={3}'.format(self.serial.port, command, data, retry_count))
        return success


def discover(idxOffset, *args, **kwargs):
    nodes = []

    config = kwargs['config']
    if 'SERIAL_PORTS' in config:
        for index, comm in enumerate(config['SERIAL_PORTS']):
            node = SerialNode(index+idxOffset, comm)
            print("Serial node {0} found at port {1}".format(index+idxOffset+1, node.serial.name))
            nodes.append(node)

    gevent.sleep(BOOTLOADER_CHILL_TIME)
    return nodes
