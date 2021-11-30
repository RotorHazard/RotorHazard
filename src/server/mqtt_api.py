from helpers.mqtt_helper import make_topic, split_topic
from interface.BaseHardwareInterface import BaseHardwareInterface
from server.RHUtils import FREQS
import json


class MqttAPI:
    def __init__(self, client, ann_topic, timer_id, INTERFACE,
                 node_crossing_callback,
                 pass_record_callback,
                 on_set_frequency,
                 on_set_enter_at_level,
                 on_set_exit_at_level):
        self.client = client
        self.ann_topic = ann_topic
        self.timer_id = timer_id
        self.INTERFACE = INTERFACE
        self.node_crossing_callback = node_crossing_callback
        self.pass_record_callback = pass_record_callback
        self.on_set_frequency = on_set_frequency
        self.on_set_enter_at_level = on_set_enter_at_level
        self.on_set_exit_at_level = on_set_exit_at_level

    def _subscribe_to(self, node_topic, handler):
        topic = make_topic(self.ann_topic, [self.timer_id, '+', '+', node_topic])
        self.client.message_callback_add(topic, handler)
        self.client.subscribe(topic)

    def _unsubscibe_from(self, node_topic):
        topic = make_topic(self.ann_topic, [self.timer_id, '+', '+', node_topic])
        self.client.unsubscribe(topic)
        self.client.message_callback_remove(topic)

    def start(self):
        self._subscribe_to('enter', self.enter_handler)
        self._subscribe_to('exit', self.exit_handler)
        self._subscribe_to('pass', self.pass_handler)
        self._subscribe_to('frequency', self.set_frequency_handler)
        self._subscribe_to('bandChannel', self.set_bandChannel_handler)
        self._subscribe_to('enterTrigger', self.set_enter_handler)
        self._subscribe_to('exitTrigger', self.set_exit_handler)

    def stop(self):
        self._unsubscibe_from('enter')
        self._unsubscibe_from('exit')
        self._unsubscibe_from('pass')
        self._unsubscibe_from('frequency')
        self._unsubscibe_from('bandChannel')
        self._unsubscibe_from('enterTrigger')
        self._unsubscibe_from('exitTrigger')

    def _get_node_from_topic(self, topic):
        topicNames = split_topic(topic)
        if len(topicNames) >= 4:
            timer_id = topicNames[-4]
            nm_name = topicNames[-3]
            multi_node_index = int(topicNames[-2])
            if timer_id == self.timer_id:
                for node_manager in self.INTERFACE.node_managers:
                    if node_manager.addr == nm_name and multi_node_index < len(node_manager.nodes):
                        return node_manager.nodes[multi_node_index]
        return None

    def enter_handler(self, client, userdata, msg):
        node = self._get_node_from_topic(msg.topic)
        if node:
            node.crossing_flag = True
            self.node_crossing_callback(node)

    def exit_handler(self, client, userdata, msg):
        node = self._get_node_from_topic(msg.topic)
        if node:
            node.crossing_flag = False
            self.node_crossing_callback(node)

    def pass_handler(self, client, userdata, msg):
        node = self._get_node_from_topic(msg.topic)
        if node:
            pass_info = json.loads(msg.payload.decode('utf-8'))
            if pass_info['source'] == 'realtime':
                lap_source = BaseHardwareInterface.LAP_SOURCE_REALTIME
            elif pass_info['source'] == 'manual':
                lap_source = BaseHardwareInterface.LAP_SOURCE_MANUAL
            else:
                lap_source = None

            if lap_source:
                lap_ts = float(pass_info['timestamp'])
                self.pass_record_callback(node, lap_ts, lap_source)

    def set_frequency_handler(self, client, userdata, msg):
        node = self._get_node_from_topic(msg.topic)
        if node:
            freq = int(msg.payload.decode('utf-8'))
            self.on_set_frequency({'node': node.index, 'frequency': freq})

    def set_bandChannel_handler(self, client, userdata, msg):
        node = self._get_node_from_topic(msg.topic)
        if node:
            bc = msg.payload.decode('utf-8')
            if bc in FREQS:
                freq = FREQS[bc]
                self.on_set_frequency({'node': node.index, 'frequency': freq, 'band': bc[0], 'channel': int(bc[1])})

    def set_enter_handler(self, client, userdata, msg):
        node = self._get_node_from_topic(msg.topic)
        if node:
            level = int(msg.payload.decode('utf-8'))
            self.on_set_enter_at_level({'node': node.index, 'enter_at_level': level})

    def set_exit_handler(self, client, userdata, msg):
        node = self._get_node_from_topic(msg.topic)
        if node:
            level = int(msg.payload.decode('utf-8'))
            self.on_set_exit_at_level({'node': node.index, 'exit_at_level': level})
