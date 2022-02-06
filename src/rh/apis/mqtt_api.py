from rh.helpers.mqtt_helper import make_topic, split_topic
from rh.interface import RssiSample
from rh.interface.BaseHardwareInterface import BaseHardwareInterface, BaseHardwareInterfaceListener
from rh.util.RHUtils import FREQS
from . import NodeRef, RESET_FREQUENCY
import logging
import json


logger = logging.getLogger(__name__)


def get_rssi_sample(payload):
    ts = int(payload['timestamp'])
    rssi = int(payload['rssi']) if 'rssi' in payload else None
    return RssiSample(ts, rssi)


class MqttAPI:
    def __init__(self, mqtt_client, ann_topic: str, timer_id: str, hw: BaseHardwareInterface, listener: BaseHardwareInterfaceListener):
        self.hw_interface = hw
        self.listener = listener
        self.client = mqtt_client
        self.ann_topic = ann_topic
        self.timer_id = timer_id

    def _subscribe_to(self, node_topic, handler):
        timer_topic = self.timer_id if self.timer_id is not None else '+'
        topic = make_topic(self.ann_topic, [timer_topic, '+', '+', node_topic])
        self.client.message_callback_add(topic, handler)
        self.client.subscribe(topic)

    def _unsubscibe_from(self, node_topic):
        timer_topic = self.timer_id if self.timer_id is not None else '+'
        topic = make_topic(self.ann_topic, [timer_topic, '+', '+', node_topic])
        self.client.unsubscribe(topic)
        self.client.message_callback_remove(topic)

    def start(self):
        logger.info('MQTT API started')
        self._subscribe_to('enter', self.enter_handler)
        self._subscribe_to('exit', self.exit_handler)
        self._subscribe_to('pass', self.pass_handler)
        self._subscribe_to('sample', self.sample_handler)
        self._subscribe_to('frequency', self.set_frequency_handler)
        self._subscribe_to('bandChannel', self.set_bandChannel_handler)
        self._subscribe_to('enterTrigger', self.set_enter_handler)
        self._subscribe_to('exitTrigger', self.set_exit_handler)

    def stop(self):
        self._unsubscibe_from('enter')
        self._unsubscibe_from('exit')
        self._unsubscibe_from('pass')
        self._unsubscibe_from('sample')
        self._unsubscibe_from('frequency')
        self._unsubscibe_from('bandChannel')
        self._unsubscibe_from('enterTrigger')
        self._unsubscibe_from('exitTrigger')
        logger.info('MQTT API stopped')

    def _get_node_ref_from_topic(self, topic):
        topic_names = split_topic(topic)
        if len(topic_names) >= 4:
            timer_id = topic_names[-4]
            nm_addr = topic_names[-3]
            multi_node_index = int(topic_names[-2])
            if timer_id == self.timer_id:
                for node_manager in self.hw_interface.node_managers:
                    if node_manager.addr == nm_addr and multi_node_index < len(node_manager.nodes):
                        node = node_manager.nodes[multi_node_index]
                        return NodeRef(timer_id, nm_addr, multi_node_index, node)
            else:
                return NodeRef(timer_id, nm_addr, multi_node_index, None)
        return None

    def enter_handler(self, client, userdata, msg):
        node_ref = self._get_node_ref_from_topic(msg.topic)
        if node_ref:
            enter_info = json.loads(msg.payload.decode('utf-8'))
            ts, rssi = get_rssi_sample(enter_info)
            self.listener.on_enter_triggered(node_ref, ts, rssi)

    def exit_handler(self, client, userdata, msg):
        node_ref = self._get_node_ref_from_topic(msg.topic)
        if node_ref:
            exit_info = json.loads(msg.payload.decode('utf-8'))
            ts, rssi = get_rssi_sample(exit_info)
            self.listener.on_exit_triggered(node_ref, ts, rssi)

    def pass_handler(self, client, userdata, msg):
        node_ref = self._get_node_ref_from_topic(msg.topic)
        if node_ref:
            pass_info = json.loads(msg.payload.decode('utf-8'))
            if pass_info['source'] == 'realtime':
                lap_source = BaseHardwareInterface.LAP_SOURCE_REALTIME
            elif pass_info['source'] == 'manual':
                lap_source = BaseHardwareInterface.LAP_SOURCE_MANUAL
            else:
                lap_source = None
            if lap_source is not None:
                ts, rssi = get_rssi_sample(pass_info)
                self.listener.on_pass(node_ref, ts, lap_source, rssi)

    def sample_handler(self, client, userdata, msg):
        node_ref = self._get_node_ref_from_topic(msg.topic)
        if node_ref:
            sample_info = json.loads(msg.payload.decode('utf-8'))
            ts, rssi = get_rssi_sample(sample_info)
            self.listener.on_rssi_sample(node_ref, ts, rssi)

    def set_frequency_handler(self, client, userdata, msg):
        node_ref = self._get_node_ref_from_topic(msg.topic)
        if node_ref:
            try:
                if msg.payload:
                    freq_bandChannel = msg.payload.decode('utf-8').split(',')
                    freq = int(freq_bandChannel[0])
                    if len(freq_bandChannel) >= 2:
                        bandChannel = freq_bandChannel[1]
                        band = bandChannel[0]
                        channel = int(bandChannel[1])
                    else:
                        band = None
                        channel = None
                    self.listener.on_frequency_changed(node_ref, freq, band, channel)
                else:
                    self.listener.on_frequency_changed(node_ref, 0)
            except:
                logger.warning('Invalid frequency message')

    def set_bandChannel_handler(self, client, userdata, msg):
        node_ref = self._get_node_ref_from_topic(msg.topic)
        if node_ref:
            if msg.payload:
                bandChannel = msg.payload.decode('utf-8')
                if bandChannel in FREQS:
                    freq = FREQS[bandChannel]
                    band = bandChannel[0]
                    channel = int(bandChannel[1])
                    self.listener.on_frequency_changed(node_ref, freq, band, channel)
            else:
                self.listener.on_frequency_changed(node_ref, RESET_FREQUENCY)

    def set_enter_handler(self, client, userdata, msg):
        node_ref = self._get_node_ref_from_topic(msg.topic)
        if node_ref:
            try:
                level = int(msg.payload.decode('utf-8'))
                self.listener.on_enter_trigger_changed(node_ref, level)
            except:
                logger.warning('Invalid enter trigger message')

    def set_exit_handler(self, client, userdata, msg):
        node_ref = self._get_node_ref_from_topic(msg.topic)
        if node_ref:
            try:
                level = int(msg.payload.decode('utf-8'))
                self.listener.on_exit_trigger_changed(node_ref, level)
            except:
                logger.warning('Invalid exit trigger message')
