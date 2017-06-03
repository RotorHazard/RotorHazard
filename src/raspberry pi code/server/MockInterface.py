import gevent
from random import randint

from Node import Node

class MockInterface:
    def __init__(self):
        self.update_thread = None
        self.nodes = []

        frequencies = [5685, 5760, 5800, 5860, 5905, 5645]
        for frequency in frequencies:
            node = Node()
            node.frequency = frequency
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

    def set_frequency_index(self, node_index, frequency):
        node = self.nodes[node_index]
        node.frequency = frequency
        return node.frequency

    def set_trigger_rssi_index(self, node_index, trigger_rssi):
        node = self.nodes[node_index]
        node.trigger_rssi = trigger_rssi
        return node.trigger_rssi

    def capture_trigger_rssi_index(self, node_index):
        node = self.nodes[node_index]
        node.trigger_rssi = node.current_rssi
        return node.trigger_rssi

    def log(self, message):
        string = 'MockInterface: {0}'.format(message)
        print(string)

    def get_settings_json(self):
        settings = [node.get_settings_json() for node in self.nodes]
        print(settings)
        return settings

    def get_heartbeat_json(self):
        return { 'current_rssi': [node.current_rssi for node in self.nodes]}

def get_hardware_interface():
    return MockInterface()
