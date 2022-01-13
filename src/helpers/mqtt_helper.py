import gevent
import paho.mqtt.client as mqtt_client
from collections import UserDict


def make_topic(root, parts):
    topic = root
    if root and parts:
        topic += '/'
    topic += '/'.join([p.replace('%', '%25').
                 replace('/', '%2F').
                 replace('#', '%23').
                 replace('+', '%2B') if not p in ['+', '#'] else p for p in parts])
    return topic


def split_topic(topic):
    parts = topic.split('/')
    return [p.replace('%2B', '+').
            replace('%23', '#').
            replace('%2F', '/').
            replace('%25', '%') for p in parts]


def create_client(mqttConfig, prefix):
    def get_value(key, default_value=None):
        return mqttConfig.get(prefix+key, mqttConfig.get(key, default_value))

    broker = get_value('BROKER')
    if not broker:
        raise Exception("MQTT not configured")
    client_id = get_value('CLIENT_ID')
    client = mqtt_client.Client(client_id=client_id)
    username = get_value('USERNAME')
    if username:
        client.username_pw_set(username, get_value('PASSWORD'))
    client_cert = get_value('CLIENT_CERT')
    private_key = get_value('PRIVATE_KEY')
    if client_cert and private_key:
        client.tls_set(certfile=client_cert, keyfile=private_key)
    client.connect(broker, get_value('PORT', 1883))
    gevent.spawn(client.loop_forever)
    return client


class MqttHelper(UserDict):
    def close(self):
        for client in self.data.values():
            client.disconnect()


def create(rhconfig):
    mqttConfig = rhconfig.MQTT
    timer_client = create_client(mqttConfig, 'TIMER_')
    race_client = create_client(mqttConfig, 'RACE_')
    helper = MqttHelper()
    helper['timer'] = timer_client
    helper['race'] = race_client
    return helper
