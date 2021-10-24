import logging
from .eventmanager import Evt
import paho.mqtt.client as mqtt_client
import json

logger = logging.getLogger(__name__)


class MqttEventManager:

    def __init__(self, eventmanager, data, race, config):
        self.Events = eventmanager
        self.RHData = data
        self.RACE = race
        self.config = config
        self.client = None

    def install_default_messages(self):
        if 'BROKER' in self.config:
            self.addEvent(Evt.RACE_START, race_start)
            self.addEvent(Evt.RACE_LAP_RECORDED, race_lap)
            self.addEvent(Evt.RACE_FINISH, race_finish)
            self.addEvent(Evt.RACE_STOP, race_stop)

    def start(self):
        if 'BROKER' in self.config:
            self.client = mqtt_client.Client(client_id=self.config['CLIENT_ID'] if 'CLIENT_ID' in self.config else None)
            if 'USERNAME' in self.config:
                self.client.username_pw_set(self.config['USERNAME'], self.config['PASSWORD'] if 'PASSWORD' in self.config else None)
            if 'CLIENT_CERT' in self.config and 'PRIVATE_KEY' in self.config:
                self.client.tls_set(certfile=self.config['CLIENT_CERT'], keyfile=self.config['PRIVATE_KEY'])
            self.client.connect(self.config['BROKER'], self.config['PORT'] if 'PORT' in self.config else 1883)
            self.client.loop_start()

    def addEvent(self, event, msgFunc):
        self.Events.on(event, 'MQTT', self.create_handler(msgFunc))

    def create_handler(self, func):
        def _handler(args):
            args['client'] = self.client
            args['topic'] = self.config['TOPIC']
            args['event'] = self.RHData.get_option('eventName', '')
            args['RHData'] = self.RHData
            args['RACE'] = self.RACE
            func(**args)

        return _handler


race_num = 0


def race_start(client, topic, event, RACE, **kwargs):
    global race_num
    race_num += 1
    msg = {'startTime': RACE.start_time_epoch_ms}
    client.publish("{}/{}/{}/{}".format(topic, event, race_num, RACE.current_heat), json.dumps(msg))


def race_lap(client, topic, event, RACE, node_index, timer, lap, **kwargs):
    pilot = RACE.node_pilots[node_index]
    msg = {'timestamp': lap['lap_time_stamp']}
    client.publish("{}/{}/{}/{}/{}/{}/{}".format(topic, event, race_num, RACE.current_heat, pilot.callsign, timer, lap['lap_number']), json.dumps(msg))


def race_finish(client, topic, event, RACE, **kwargs):
    msg = {'finishTime': RACE.finish_time_epoch_ms}
    client.publish("{}/{}/{}/{}".format(topic, event, race_num, RACE.current_heat), json.dumps(msg))


def race_stop(client, topic, event, RACE, **kwargs):
    msg = {'stopTime': RACE.end_time_epoch_ms}
    client.publish("{}/{}/{}/{}".format(topic, event, race_num, RACE.current_heat), json.dumps(msg))
