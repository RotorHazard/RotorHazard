''' Trackside Connector '''

import logging
from time import monotonic
from RHRace import RaceStatus
from eventmanager import Evt
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

class Tests():
    def __init__(self, rhapi):
        self._rhapi = rhapi

    def initialize(self, _args):
        logger.info('Initializing Trackside connector')

        self._rhapi.ui.socket_listen('ts_server_info', self.server_info)
        self._rhapi.ui.socket_listen('ts_server_time', self.server_time)
        self._rhapi.ui.socket_listen('ts_race_stage', self.race_stage)
        self._rhapi.ui.socket_listen('ts_race_stop', self.race_stop)

        # self._rhapi.fields.register_pilot_attribute(UIField('trackside_ID', "Trackside user ID", UIFieldType.BASIC_INT)) # , private=True
        # logger.debug(self._rhapi.db.pilot_ids_by_attribute('trackside_ID', '123'))

    def server_info(self, _arg=None):
        return self._rhapi.server_info

    def server_time(self, _arg=None):
        return monotonic()

    def race_stage(self, arg=None):
        if self._rhapi.race.status != RaceStatus.READY:
            self._rhapi.race.stop(doSave=True)

        start_race_args = {
            'secondary_format': True,
        }

        if arg.get('start_time_s'):
            start_race_args['start_time_s'] = arg['start_time_s']

        self._rhapi.race.stage(start_race_args)

    def race_stop(self, arg=None):
        self._rhapi.race.stop()

def initialize(rhapi):
    connector = Tests(rhapi)
    rhapi.events.on(Evt.STARTUP, connector.initialize)

