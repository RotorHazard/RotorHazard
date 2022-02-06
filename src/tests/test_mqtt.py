import unittest
from rh.interface.BaseHardwareInterface import BaseHardwareInterface,\
    BaseHardwareInterfaceListener
from rh.interface.MockInterface import MockInterface
from rh.interface.MqttInterface import MqttInterface
from rh.apis.mqtt_api import MqttAPI
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
        ann_topic = '/ann'
        ctrl_topic = '/ctrl'
        timer_id = 'local'
        hw = MockInterface(1)
        intf = MqttInterface(StubMqttClient(), ann_topic, ctrl_topic, timer_id, hw)
        msg = {
            'topic': intf._mqtt_create_node_topic('system', hw.nodes[0], "frequency"),
            'payload': '5675'
        }
        intf._mqtt_set_frequency(hw.node_managers[0], None, None, StubMqttMessage(**msg))
        self.assertEqual(hw.nodes[0].frequency, 5675)

    def test_mqtt_frequency_bandChannel(self):
        ann_topic = '/ann'
        ctrl_topic = '/ctrl'
        timer_id = 'local'
        hw = MockInterface(1)
        intf = MqttInterface(StubMqttClient(), ann_topic, ctrl_topic, timer_id, hw)
        msg = {
            'topic': intf._mqtt_create_node_topic('system', hw.nodes[0], "frequency"),
            'payload': '5675,X4'
        }
        intf._mqtt_set_frequency(hw.node_managers[0], None, None, StubMqttMessage(**msg))
        self.assertEqual(hw.nodes[0].frequency, 5675)
        self.assertEqual(hw.nodes[0].bandChannel, 'X4')

    def test_mqtt_bandChannel(self):
        ann_topic = '/ann'
        ctrl_topic = '/ctrl'
        timer_id = 'local'
        hw = MockInterface(1)
        intf = MqttInterface(StubMqttClient(), ann_topic, ctrl_topic, timer_id, hw)
        msg = {
            'topic': intf._mqtt_create_node_topic('system', hw.nodes[0], "bandChannel"),
            'payload': 'R8'
        }
        intf._mqtt_set_bandChannel(hw.node_managers[0], None, None, StubMqttMessage(**msg))
        self.assertEqual(hw.nodes[0].frequency, 5917)
        self.assertEqual(hw.nodes[0].bandChannel, 'R8')

    def test_mqtt_pass_handler_realtime(self):
        self.check_mqtt_pass_handler('realtime', BaseHardwareInterface.LAP_SOURCE_REALTIME)

    def test_mqtt_pass_handler_manual(self):
        self.check_mqtt_pass_handler('manual', BaseHardwareInterface.LAP_SOURCE_MANUAL)

    def check_mqtt_pass_handler(self, mqtt_lap_source, expected_lap_source):
        ann_topic = '/ann'
        ctrl_topic = '/ctrl'
        timer_id = 'local'
        new_lap_ts = None
        new_lap_source = None
        def pass_callback(node, lap_ts, lap_source, lap_rssi):
            nonlocal new_lap_ts
            nonlocal new_lap_source
            new_lap_ts = lap_ts
            new_lap_source = lap_source

        listener = BaseHardwareInterfaceListener()
        listener.on_pass = pass_callback
        hw = MockInterface(1)
        api = MqttAPI(StubMqttClient(), ann_topic, timer_id, hw, listener)
        api.ann_topic = ann_topic
        api.timer_id = timer_id

        intf = MqttInterface(StubMqttClient(), ann_topic, ctrl_topic, timer_id, hw)
        intf.ann_topic = ann_topic
        intf.timer_id = timer_id
        msg = {
            'topic': intf._mqtt_create_node_topic(ann_topic, hw.nodes[0], 'pass'),
            'payload': json.dumps({
                'source': mqtt_lap_source,
                'timestamp': 11,
                'rssi': 49
            })
        }
        api.pass_handler(api.client, None, StubMqttMessage(**msg))
        self.assertEqual(new_lap_ts, 11)
        self.assertEqual(new_lap_source, expected_lap_source)

    def test_frequency_handler(self):
        ann_topic = '/ann'
        ctrl_topic = '/ctrl'
        timer_id = 'local'
        new_freq = None
        def set_frequency_callback(node, frequency, band=None, channel=None):
            nonlocal new_freq
            new_freq = frequency

        listener = BaseHardwareInterfaceListener()
        listener.on_frequency_changed = set_frequency_callback
        hw = MockInterface(1)
        api = MqttAPI(StubMqttClient(), ann_topic, timer_id, hw, listener)

        intf = MqttInterface(StubMqttClient(), ann_topic, ctrl_topic, timer_id, hw)
        msg = {
            'topic': intf._mqtt_create_node_topic(ann_topic, hw.nodes[0], 'frequency'),
            'payload': '5808'
        }
        api.set_frequency_handler(api.client, None, StubMqttMessage(**msg))
        self.assertEqual(new_freq, 5808)


if __name__ == '__main__':
    unittest.main()
