''' Pilot Prefered Band Selector '''

import logging
from eventmanager import Evt
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

class PilotPreferedBandSelector():
    def __init__(self, rhapi):
        self._rhapi = rhapi
        self.enabled = True

    def initialize(self, _args):
        logger.info('Initializing Pilot Prefered Band Selector')
        options=[
            UIFieldSelectOption('raceband', "RACEBAND"),
            UIFieldSelectOption('dji', "DJI"),
        ]
        self._rhapi.fields.register_pilot_attribute(
            UIField('prefered_band', "Prefered Band", UIFieldType.SELECT,
                    options=options, value='raceband'))

def initialize(rhapi):
    s = PilotPreferedBandSelector(rhapi)
    rhapi.events.on(Evt.STARTUP, s.initialize)

