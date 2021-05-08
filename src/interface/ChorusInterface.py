'''Chorus hardware interface layer.'''

import logging
import gevent.lock
import serial

from .Node import Node
from .BaseHardwareInterface import BaseHardwareInterface

RETRY_COUNT=5

logger = logging.getLogger(__name__)

class SerialLine:
    def __init__(self, serial_io):
        self.serial_io = serial_io
        self.lock = gevent.lock.RLock()

    def write(self, data):
        self.serial_io.write(data.encode('UTF-8'))

    def read(self):
        return self.serial_io.read_until()[:-1]

    def __enter__(self):
        self.lock.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.__exit__(exc_type, exc_value, traceback)

class ChorusNode(Node):
    def __init__(self, index, io_line):
        super().__init__(index=index, io_line=io_line)
        self.api_valid_flag = True

    def send_command(self, command, in_value):
        with self.io_line:
            self.io_line.write('R{0}{1}{2:04x}\n'.format(self.index, command, in_value))
            out_value = int(self.io_line.read()[3:7], 16)
            return out_value

    def set_and_validate_value_4x(self, command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count < RETRY_COUNT:
            out_value = self.send_command(command, in_value)
            if out_value == in_value:
                success = True
            else:
                retry_count += 1
                logger.warning('Value Not Set (retry={0}): cmd={1}, val={2}, node={3}'.\
                         format(retry_count, command, in_value, self.index+1))
        return out_value if out_value is not None else in_value
            
class ChorusInterface(BaseHardwareInterface):
    def __init__(self, serial_io):
        super().__init__()
        self.serial_line = SerialLine(serial_io)
        self.update_thread = None # Thread for running the main update loop

        with self.serial_line:
            self.serial_line.write('N0\n')
            resp = self.serial_line.read()
            if resp:
                last_node = resp[1]
            else:
                logger.warning("Invalid response received")
        self.nodes = [] # Array to hold each node object

        for index in range(int(last_node)):
            node = ChorusNode(index, self.serial_line)
            self.nodes.append(node)

        with self.serial_line:
            self.serial_line.write('R*R2\n')
            self.serial_line.read()
            for node in self.nodes:
                node.set_and_validate_value_4x('M', 0)

    #
    # Update Loop
    #

    def _update(self):
        with self.serial_line:
            data = self.serial_line.read()
        if data:
            self._process_message(data)

    def _process_message(self, data):
        if data[0] == 'S':
            node_addr = data[1]
            cmd = data[2]
            if cmd == 'L':
                lap_id = int(data[3:5], 16)
                lap_ts = int(data[5:13], 16)
                gevent.spawn(self.pass_record_callback, int(node_addr), lap_ts, BaseHardwareInterface.LAP_SOURCE_REALTIME, 0)

    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency):
        node = self.nodes[node_index]
        node.debug_pass_count = 0  # reset debug pass count on frequency change
        if frequency:
            node.frequency = node.set_and_validate_value_4x('F', frequency)
        else:  # if freq=0 (node disabled) then write default freq, but save 0 value
            node.set_and_validate_value_4x('F', 5800)
            node.frequency = 0

    def transmit_enter_at_level(self, node, level):
        return node.set_and_validate_value_4x('T', level)

    def transmit_exit_at_level(self, node, level):
        return node.set_and_validate_value_4x('T', level)

    def force_end_crossing(self, node_index):
        node = self.nodes[node_index]

def get_hardware_interface(*args, **kwargs):
    '''Returns the interface object.'''
    port = kwargs['config'].CHORUS['HARDWARE_PORT']
    serial_io = serial.Serial(port=port, baudrate=115200, timeout=0.1)
    return ChorusInterface(serial_io)
