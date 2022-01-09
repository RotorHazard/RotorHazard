import unittest
from interface.MockInterface import MockInterface
from interface.MqttInterface import MqttInterface


class StubMqttClient:
    def publish(self, topic, payload):
        pass


class StubMqttMessage:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload.encode('utf-8')


class MqttTest(unittest.TestCase):

    def test_mqtt_frequency(self):
        hw = MockInterface(1)
        intf = MqttInterface(StubMqttClient(), hw)
        intf.ann_topic = '/ann'
        intf.ctrl_topic = '/ctrl'
        intf.timer_id = 'local'
        msg = {
            'topic': intf._mqtt_create_node_topic('system', hw.nodes[0], "frequency"),
            'payload': '5675'
        }
        intf._mqtt_set_frequency(hw.node_managers[0], None, None, StubMqttMessage(**msg))
        self.assertEqual(hw.nodes[0].frequency, 5675)

    def test_mqtt_frequency_bandChannel(self):
        hw = MockInterface(1)
        intf = MqttInterface(StubMqttClient(), hw)
        intf.ann_topic = '/ann'
        intf.ctrl_topic = '/ctrl'
        intf.timer_id = 'local'
        msg = {
            'topic': intf._mqtt_create_node_topic('system', hw.nodes[0], "frequency"),
            'payload': '5675,X4'
        }
        intf._mqtt_set_frequency(hw.node_managers[0], None, None, StubMqttMessage(**msg))
        self.assertEqual(hw.nodes[0].frequency, 5675)
        self.assertEqual(hw.nodes[0].bandChannel, 'X4')

    def test_mqtt_bandChannel(self):
        hw = MockInterface(1)
        intf = MqttInterface(StubMqttClient(), hw)
        intf.ann_topic = '/ann'
        intf.ctrl_topic = '/ctrl'
        intf.timer_id = 'local'
        msg = {
            'topic': intf._mqtt_create_node_topic('system', hw.nodes[0], "bandChannel"),
            'payload': 'R8'
        }
        intf._mqtt_set_bandChannel(hw.node_managers[0], None, None, StubMqttMessage(**msg))
        self.assertEqual(hw.nodes[0].frequency, 5917)
        self.assertEqual(hw.nodes[0].bandChannel, 'R8')


if __name__ == '__main__':
    unittest.main()
