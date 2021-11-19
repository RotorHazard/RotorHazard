import logging
from .eventmanager import Evt
from helpers.mqtt_helper import make_topic
import json

logger = logging.getLogger(__name__)


class MqttEventManager:

    def __init__(self, eventmanager, data, race, config, mqttClient):
        self.Events = eventmanager
        self.RHData = data
        self.RACE = race
        self.config = config
        self.client = mqttClient

    def install_default_messages(self):
        if self.client:
            self.addEvent(Evt.RACE_START, race_start)
            self.addEvent(Evt.RACE_LAP_RECORDED, race_lap)
            self.addEvent(Evt.RACE_FINISH, race_finish)
            self.addEvent(Evt.RACE_STOP, race_stop)

    def addEvent(self, event, msgFunc):
        self.Events.on(event, 'MQTT', self.create_handler(msgFunc))

    def create_handler(self, func):
        def _handler(args):
            args['client'] = self.client
            args['topic'] = self.config['RACE_ANN_TOPIC']
            args['event'] = self.RHData.get_option('eventName', '')
            args['RHData'] = self.RHData
            args['RACE'] = self.RACE
            func(**args)

        return _handler


def race_start(client, topic, event, RACE, **kwargs):
    msg = {'startTime': RACE.start_time_epoch_ms}
    client.publish(make_topic(topic, [event, RACE.current_round, RACE.current_heat]), json.dumps(msg))


def race_lap(client, topic, event, RACE, node_index, lap, timer, **kwargs):
    pilot = RACE.node_pilots[node_index]
    msg = {'timestamp': lap['lap_time_stamp']}
    client.publish(make_topic(topic, [event, RACE.current_round, RACE.current_heat, pilot.callsign, str(lap['lap_number']), timer]), json.dumps(msg))


def race_finish(client, topic, event, RACE, **kwargs):
    msg = {'finishTime': RACE.finish_time_epoch_ms}
    client.publish(make_topic(topic, [event, RACE.current_round, RACE.current_heat]), json.dumps(msg))


def race_stop(client, topic, event, RACE, **kwargs):
    msg = {'stopTime': RACE.end_time_epoch_ms}
    client.publish(make_topic(topic, [event, RACE.current_round, RACE.current_heat]), json.dumps(msg))
