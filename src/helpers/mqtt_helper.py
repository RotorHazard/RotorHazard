import paho.mqtt.client as mqtt_client


def make_topic(root, parts):
    topic = root
    if root and parts:
        topic += '/'
    topic += '/'.join([p.replace('%', '%25').
                 replace('/', '%2F').
                 replace('#', '%23').
                 replace('+', '%2B') if len(p) > 1 else p for p in parts])
    return topic


def split_topic(topic):
    parts = topic.split('/')
    return [p.replace('%2B', '+').
            replace('%23', '#').
            replace('%2F', '/').
            replace('%25', '%') for p in parts]


def create(rhconfig):
    client = None
    mqttConfig = rhconfig.MQTT
    if 'BROKER' in mqttConfig and mqttConfig['BROKER']:
        client_id = mqttConfig['CLIENT_ID'] if 'CLIENT_ID' in mqttConfig else None
        client = mqtt_client.Client(client_id=client_id)
        if 'USERNAME' in mqttConfig and mqttConfig['USERNAME']:
            client.username_pw_set(mqttConfig['USERNAME'], mqttConfig['PASSWORD'] if 'PASSWORD' in mqttConfig else None)
        if 'CLIENT_CERT' in mqttConfig and mqttConfig['CLIENT_CERT'] and 'PRIVATE_KEY' in mqttConfig and mqttConfig['PRIVATE_KEY']:
            client.tls_set(certfile=mqttConfig['CLIENT_CERT'], keyfile=mqttConfig['PRIVATE_KEY'])
        client.connect(mqttConfig['BROKER'], mqttConfig['PORT'] if 'PORT' in mqttConfig else 1883)
        client.loop_start()
    return client
