'''Chorus hardware interface layer.'''

import logging
import gevent # For threads and timing
from gevent.lock import BoundedSemaphore
import serial

from .Node import Node
from .BaseHardwareInterface import BaseHardwareInterface

RETRY_COUNT=5

logger = logging.getLogger(__name__)

class ChorusInterface(BaseHardwareInterface):
    def __init__(self, serial_io):
        super().__init__()
        self.serial_io = serial_io
        self.semaphore = BoundedSemaphore(1)
        self.update_thread = None # Thread for running the main update loop

        with self.semaphore:
            self.write('N0\n')
            resp = self.read()
            if resp:
                last_node = resp[1]
            else:
                logger.warning("Invalid response received")
        self.nodes = [] # Array to hold each node object

        for index in range(int(last_node)):
            node = Node()
            node.index = index
            node.api_valid_flag = True
            self.nodes.append(node)

        with self.semaphore:
            self.write('R*R2\n')
            self.read()
            for node in self.nodes:
                self.write('R{0}M00\n'.format(node.index))
                self.read()


    #
    # Update Loop
    #

    def start(self):
        if self.update_thread is None:
            logger.info('Starting background thread.')
            self.update_thread = gevent.spawn(self.update_loop)

    def update(self):
        with self.semaphore:
            data = self.read()
        if data:
            if data[0] == 'S':
                node_addr = data[1]
                cmd = data[2]
                if cmd == 'L':
                    lap_id = int(data[3:5], 16)
                    lap_ts = int(data[5:13], 16)
                    gevent.spawn(self.pass_record_callback, int(node_addr), lap_ts, BaseHardwareInterface.LAP_SOURCE_REALTIME, 0)


    def write(self, data):
        self.serial_io.write(data.encode('UTF-8'))

    def read(self):
        return self.serial_io.read_until()[:-1]

    def set_and_validate_value_2(self, node, command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count < RETRY_COUNT:
            with self.semaphore:
                self.write('R{0}{1}{2:04x}\n'.format(node.index, command, in_value))
                out_value = int(self.read()[3:7], 16)
            if out_value == in_value:
                success = True
            else:
                retry_count = retry_count + 1
                logger.warning('Value 2v Not Set (retry={0}): cmd={1}, val={2}, node={3}'.\
                         format(retry_count, command, in_value, node.index))

        if out_value == None:
            out_value = in_value
        return out_value

    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency):
        node = self.nodes[node_index]
        node.debug_pass_count = 0  # reset debug pass count on frequency change
        if frequency:
            node.frequency = self.set_and_validate_value_2(node, 'F', frequency)
        else:  # if freq=0 (node disabled) then write default freq, but save 0 value
            self.set_and_validate_value_2(node, 'F', 5800)
            node.frequency = 0

    def transmit_enter_at_level(self, node, level):
        return self.set_and_validate_value_2(node, 'T', level)

    def transmit_exit_at_level(self, node, level):
        return self.set_and_validate_value_2(node, 'T', level)

    def force_end_crossing(self, node_index):
        node = self.nodes[node_index]

def get_hardware_interface(*args, **kwargs):
    '''Returns the interface object.'''
    port = kwargs['config'].CHORUS['HARDWARE_PORT']
    serial_io = serial.Serial(port=port, baudrate=115200, timeout=0.1)
    return ChorusInterface(serial_io)
