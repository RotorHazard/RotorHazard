import logging
from interface.MqttInterface import MqttInterface
from interface.LapRFInterface import LapRFInterfaceListener

logger = logging.getLogger(__name__)


class MqttLapRFInterface(MqttInterface, LapRFInterfaceListener):

    def __init__(self, mqtt_client, hw_interface):
        super().__init__(mqtt_client=mqtt_client, hw_interface=hw_interface)

    def on_threshold_changed(self, node, threshold):
        self._mqtt_publish_threshold(node, threshold)

    def on_gain_changed(self, node, gain):
        self._mqtt_publish_gain(node, gain)

    def _mqtt_node_manager_start(self, node_manager):
        self._mqtt_node_subscribe_to(node_manager, "threshold", self._mqtt_set_threshold)
        self._mqtt_node_subscribe_to(node_manager, "gain", self._mqtt_set_gain)
        super()._mqtt_node_manager_start(node_manager)

    def _mqtt_node_start(self, node):
        super()._mqtt_node_start(node)
        self._mqtt_publish_threshold(node, node.threshold)
        self._mqtt_publish_gain(node, node.gain)

    def _mqtt_set_threshold(self, node_manager, client, userdata, msg):
        node = self._mqtt_get_node_from_topic(node_manager, msg.topic)
        if node:
            try:
                level = int(msg.payload.decode('utf-8'))
                self.hw_interface.set_threshold(node.index, level)
            except:
                logger.warning('Invalid threshold message')

    def _mqtt_set_gain(self, node_manager, client, userdata, msg):
        node = self._mqtt_get_node_from_topic(node_manager, msg.topic)
        if node:
            try:
                level = int(msg.payload.decode('utf-8'))
                self.hw_interface.set_gain(node.index, level)
            except:
                logger.warning('Invalid gain message')

    def _mqtt_publish_threshold(self, node, threshold):
        self.client.publish(self._mqtt_create_node_topic(self.ann_topic, node, "threshold"), str(threshold))

    def _mqtt_publish_gain(self, node, gain):
        self.client.publish(self._mqtt_create_node_topic(self.ann_topic, node, "gain"), str(gain))

