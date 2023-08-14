''' Trackside Connector '''

import logging
import json
from time import monotonic
from RHRace import RaceStatus
from eventmanager import Evt
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

class TracksideConnector():
    def __init__(self, rhapi):
        self._rhapi = rhapi
        self.enabled = False

        self._rhapi.events.on(Evt.RACE_LAP_RECORDED, self.race_lap_recorded)

    def initialize(self, _args):
        logger.info('Initializing Trackside connector')

        self._rhapi.ui.socket_listen('ts_server_info', self.server_info)
        self._rhapi.ui.socket_listen('ts_server_time', self.server_time)
        self._rhapi.ui.socket_listen('ts_frequency_setup', self.frequency_setup)
        self._rhapi.ui.socket_listen('ts_race_stage', self.race_stage)
        self._rhapi.ui.socket_listen('ts_race_stop', self.race_stop)

        # self._rhapi.fields.register_pilot_attribute(UIField('trackside_ID', "Trackside user ID", UIFieldType.BASIC_INT)) # , private=True
        # logger.debug(self._rhapi.db.pilot_ids_by_attribute('trackside_ID', '123'))

    def server_info(self, _arg=None):
        self.enabled = True
        return self._rhapi.server_info

    def server_time(self, _arg=None):
        self.enabled = True
        return monotonic()

    def frequency_setup(self, arg=None):
        self.enabled = True
        set_id = self._rhapi.race.frequencyset
        frequencies = json.loads(self._rhapi.db.frequencyset_by_id(set_id))
        for seat in arg:
            frequencies[seat] = arg[seat]

        self._rhdata.db.frequencyset_alter(set_id, frequencies=frequencies)

    def race_stage(self, arg=None):
        self.enabled = True
        if self._rhapi.race.status != RaceStatus.READY:
            self._rhapi.race.stop(doSave=True)

        start_race_args = {
            'secondary_format': True,
        }

        if arg.get('start_time_s'):
            start_race_args['start_time_s'] = arg['start_time_s']

        self._rhapi.race.stage(start_race_args)

    def race_lap_recorded(self, args):
        if self.enabled:
            lap_ts = self._rhapi.race.start_time_internal + (args['lap']['lap_time_stamp'] / 1000)
            payload = {
                'seat': args['node_index'],
                'server_timestamp': lap_ts,
            }
            self._rhapi.ui.socket_broadcast('ts_lap_data', payload)

    def race_stop(self, arg=None):
        self._rhapi.race.stop()

def initialize(rhapi):
    connector = TracksideConnector(rhapi)
    rhapi.events.on(Evt.STARTUP, connector.initialize)

