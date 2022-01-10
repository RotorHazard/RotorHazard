import unittest
from interface.BaseHardwareInterface import BaseHardwareInterface
from interface.MockInterface import MockInterface
from interface.MqttInterface import MqttInterface
from server.mqtt_api import MqttAPI
import json


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

    def test_mqtt_pass_realtime(self):
        self.check_mqtt_pass('realtime', BaseHardwareInterface.LAP_SOURCE_REALTIME)

    def test_mqtt_pass_manual(self):
        self.check_mqtt_pass('manual', BaseHardwareInterface.LAP_SOURCE_MANUAL)

    def check_mqtt_pass(self, mqtt_lap_source, expected_lap_source):
        hw = MockInterface(1)
        ann_topic = '/ann'
        timer_id = 'local'
        new_lap_ts = None
        new_lap_source = None
        def pass_record_callback(node, lap_ts, lap_source):
            nonlocal new_lap_ts
            nonlocal new_lap_source
            new_lap_ts = lap_ts
            new_lap_source = lap_source
        api = MqttAPI(StubMqttClient(), ann_topic, timer_id, hw,
                      None, pass_record_callback, None, None, None, None)

        intf = MqttInterface(StubMqttClient(), hw)
        intf.ann_topic = ann_topic
        intf.timer_id = timer_id
        msg = {
            'topic': intf._mqtt_create_node_topic(ann_topic, hw.nodes[0], 'pass'),
            'payload': json.dumps({
                'source': mqtt_lap_source,
                'timestamp': 11
            })
        }
        api.pass_handler(api.client, None, StubMqttMessage(**msg))
        self.assertEqual(new_lap_ts, 11)
        self.assertEqual(new_lap_source, expected_lap_source)


if __name__ == '__main__':
    unittest.main()
