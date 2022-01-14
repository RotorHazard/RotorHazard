from .BaseHardwareInterface import BaseHardwareInterface, BaseHardwareInterfaceListener
from helpers.mqtt_helper import make_topic, split_topic
from rh.util import RHTimeFns
from rh.util.RHUtils import FREQS
import logging
import json

logger = logging.getLogger(__name__)


class MqttInterface(BaseHardwareInterfaceListener):

    def __init__(self, mqtt_client, hw_interface):
        self.hw_interface = hw_interface
        self.hw_interface.listener = self
        self.client = mqtt_client
        self.ann_topic = None
        self.ctrl_topic = None
        self.timer_id = None

    def start(self):
        for node_manager in self.hw_interface.node_managers:
            self._mqtt_node_manager_start(node_manager)
            for node in node_manager.nodes:
                self._mqtt_node_start(node)

    def stop(self):
        for node_manager in self.hw_interface.node_managers:
            self._mqtt_node_manager_stop(node_manager)

    def on_enter_triggered(self, node, cross_ts, cross_rssi):
        self._mqtt_publish_enter(node, cross_ts, cross_rssi)

    def on_exit_triggered(self, node, cross_ts, cross_rssi):
        self._mqtt_publish_exit(node, cross_ts, cross_rssi)

    def on_pass(self, node, lap_ts, lap_source, pass_rssi):
        self._mqtt_publish_pass(node, lap_ts, lap_source, pass_rssi)

    def on_frequency_changed(self, node, frequency, band=None, channel=None):
        self._mqtt_publish_bandChannel(node, band+str(channel) if band and channel else None)
        self._mqtt_publish_frequency(node, frequency)

    def on_enter_trigger_changed(self, node, level):
        self._mqtt_publish_enter_trigger(node, level)

    def on_exit_trigger_changed(self, node, level):
        self._mqtt_publish_exit_trigger(node, level)

    def _mqtt_node_manager_start(self, node_manager):
        self._mqtt_node_subscribe_to(node_manager, "frequency", self._mqtt_set_frequency)
        self._mqtt_node_subscribe_to(node_manager, "bandChannel", self._mqtt_set_bandChannel)
        self._mqtt_node_subscribe_to(node_manager, "enterTrigger", self._mqtt_set_enter_trigger)
        self._mqtt_node_subscribe_to(node_manager, "exitTrigger", self._mqtt_set_exit_trigger)
        msg = {'type': node_manager.__class__.TYPE, 'startTime': RHTimeFns.getEpochTimeNow()}
        self.client.publish(make_topic(self.ann_topic, [self.timer_id, node_manager.addr]), json.dumps(msg))

    def _mqtt_node_subscribe_to(self, node_manager, node_topic, handler):
        ctrlTopicFilter = make_topic(self.ctrl_topic, [self.timer_id, node_manager.addr, '+', node_topic])
        self.client.message_callback_add(ctrlTopicFilter, lambda client, userdata, msg: handler(node_manager, client, userdata, msg))
        self.client.subscribe(ctrlTopicFilter)

    def _mqtt_node_manager_stop(self, node_manager):
        msg = {'stopTime': RHTimeFns.getEpochTimeNow()}
        self.client.publish(make_topic(self.ann_topic, [self.timer_id, node_manager.addr]), json.dumps(msg))
        self._mqtt_node_unsubscribe_from(node_manager, "frequency")
        self._mqtt_node_unsubscribe_from(node_manager, "bandChannel")
        self._mqtt_node_unsubscribe_from(node_manager, "enterTrigger")
        self._mqtt_node_unsubscribe_from(node_manager, "exitTrigger")

    def _mqtt_node_unsubscribe_from(self, node_manager, node_topic):
        ctrlTopicFilter = make_topic(self.ctrl_topic, [self.timer_id, node_manager.addr, '+', node_topic])
        self.client.unsubscribe(ctrlTopicFilter)
        self.client.message_callback_remove(ctrlTopicFilter)

    def _mqtt_node_start(self, node):
        self._mqtt_publish_frequency(node, node.frequency)
        self._mqtt_publish_bandChannel(node, node.bandChannel)
        self._mqtt_publish_enter_trigger(node, node.enter_at_level)
        self._mqtt_publish_exit_trigger(node, node.exit_at_level)

    def _mqtt_create_node_topic(self, parent_topic, node, sub_topic=None):
        node_topic = make_topic(parent_topic, [self.timer_id, node.manager.addr, str(node.multi_node_index)])
        return node_topic+'/'+sub_topic if sub_topic else node_topic

    def _mqtt_get_node_from_topic(self, node_manager, topic):
        topicNames = split_topic(topic)
        if len(topicNames) >= 4:
            timer_id = topicNames[-4]
            nm_name = topicNames[-3]
            multi_node_index = int(topicNames[-2])
            if timer_id == self.timer_id and nm_name == node_manager.addr and multi_node_index < len(node_manager.nodes):
                return node_manager.nodes[multi_node_index]
        return None

    # incoming message handlers

    def _mqtt_set_frequency(self, node_manager, client, userdata, msg):
        node = self._mqtt_get_node_from_topic(node_manager, msg.topic)
        if node:
            if msg.payload:
                try:
                    freq_bandChannel = msg.payload.decode('utf-8').split(',')
                    freq = int(freq_bandChannel[0])
                    if len(freq_bandChannel) >= 2:
                        bandChannel = freq_bandChannel[1]
                        self.hw_interface.set_frequency(node.index, freq, bandChannel[0], int(bandChannel[1]))
                    else:
                        self.hw_interface.set_frequency(node.index, freq)
                except ValueError:
                    logger.warning("Invalid frequency message")
            else:
                self.hw_interface.set_frequency(node.index, 0)

    def _mqtt_set_bandChannel(self, node_manager, client, userdata, msg):
        node = self._mqtt_get_node_from_topic(node_manager, msg.topic)
        if node:
            if msg.payload:
                bandChannel = msg.payload.decode('utf-8')
                if bandChannel in FREQS:
                    freq = FREQS[bandChannel]
                    band = bandChannel[0]
                    channel = int(bandChannel[1])
                    self.hw_interface.set_frequency(node.index, freq, band, channel)
            else:
                self.hw_interface.set_frequency(node.index, node.frequency)

    def _mqtt_set_enter_trigger(self, node_manager, client, userdata, msg):
        node = self._mqtt_get_node_from_topic(node_manager, msg.topic)
        if node:
            try:
                level = int(msg.payload.decode('utf-8'))
                self.hw_interface.set_enter_at_level(node.index, level)
            except:
                logger.warning('Invalid enter trigger message')

    def _mqtt_set_exit_trigger(self, node_manager, client, userdata, msg):
        node = self._mqtt_get_node_from_topic(node_manager, msg.topic)
        if node:
            try:
                level = int(msg.payload.decode('utf-8'))
                self.hw_interface.set_exit_at_level(node.index, level)
            except:
                logger.warning('Invalid exit trigger message')

    # outgoing messages

    def _mqtt_publish_frequency(self, node, frequency):
        freq = str(frequency) if frequency else ''
        self.client.publish(self._mqtt_create_node_topic(self.ann_topic, node, "frequency"), freq)

    def _mqtt_publish_bandChannel(self, node, bandChannel):
        bc = bandChannel if bandChannel else ''
        self.client.publish(self._mqtt_create_node_topic(self.ann_topic, node, "bandChannel"), bc)

    def _mqtt_publish_enter_trigger(self, node, level):
        self.client.publish(self._mqtt_create_node_topic(self.ann_topic, node, "enterTrigger"), str(level))

    def _mqtt_publish_exit_trigger(self, node, level):
        self.client.publish(self._mqtt_create_node_topic(self.ann_topic, node, "exitTrigger"), str(level))

    def _mqtt_publish_enter(self, node, cross_ts, cross_rssi):
        msg = {'lap': node.pass_id+1, 'timestamp': str(cross_ts), 'rssi': cross_rssi}
        self.client.publish(self._mqtt_create_node_topic(self.ann_topic, node, "enter"), json.dumps(msg))

    def _mqtt_publish_exit(self, node, cross_ts, cross_rssi):
        msg = {'lap': node.pass_id, 'timestamp': str(cross_ts), 'rssi': cross_rssi}
        self.client.publish(self._mqtt_create_node_topic(self.ann_topic, node, "exit"), json.dumps(msg))

    def _mqtt_publish_pass(self, node, lap_ts, lap_source, pass_rssi):
        if lap_source == BaseHardwareInterface.LAP_SOURCE_REALTIME:
            lap_source_type = 'realtime'
        elif lap_source == BaseHardwareInterface.LAP_SOURCE_MANUAL:
            lap_source_type = 'manual'
        else:
            lap_source_type = None
        msg = {'lap': node.pass_id, 'timestamp': str(lap_ts), 'source': lap_source_type}
        if pass_rssi:
            msg['rssi'] = pass_rssi
        self.client.publish(self._mqtt_create_node_topic(self.ann_topic, node, "pass"), json.dumps(msg))


def get_mqtt_interface_for(hw_cls):
    import importlib
    module_parts = hw_cls.__module__.split('.')
    mqtt_module_name = '.'.join(module_parts[:-1]) + '.' + 'Mqtt' + module_parts[-1]
    try:
        mqtt_module = importlib.import_module(mqtt_module_name)
        return getattr(mqtt_module, 'Mqtt' + hw_cls.__name__)
    except (ModuleNotFoundError, AttributeError):
        logger.info('No custom MQTT hardware interface found for {} - using default'.format(hw_cls.__name__))
        return MqttInterface
