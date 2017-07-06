import gevent
from random import randint

import sys

sys.path.append('../delta5interface')
from Node import Node
from BaseHardwareInterface import BaseHardwareInterface

class MockInterface(BaseHardwareInterface):
    def __init__(self):
        BaseHardwareInterface.__init__(self)
        self.update_thread = None
        self.nodes = []
        self.calibration_threshold = 20

        frequencies = [5685, 5760, 5800, 5860, 5905, 5645]
        for index, frequency in enumerate(frequencies):
            node = Node()
            node.frequency = frequency
            node.index = index
            self.nodes.append(node)

    def update_loop(self):
        while True:
            self.update()
            gevent.sleep(0.1)

    def update(self):
        for node in self.nodes:
            node.current_rssi = randint(0,255);
            gevent.sleep(0.01)

    def start(self):
        if self.update_thread is None:
            self.log('starting background thread')
            self.update_thread = gevent.spawn(self.update_loop)

    def set_frequency(self, node_index, frequency):
        node = self.nodes[node_index]
        node.frequency = frequency

    def set_calibration_threshold_global(self, calibration_threshold):
        self.calibration_threshold = calibration_threshold

    def set_calibration_offset_global(self, calibration_offset):
        self.calibration_offset = calibration_offset

    def set_trigger_threshold_global(self, trigger_threshold):
        self.trigger_threshold = trigger_threshold

    def enable_calibration_mode(self):
        pass

    def log(self, message):
        string = 'MockInterface: {0}'.format(message)
        print(string)


def get_hardware_interface():
    return MockInterface()
