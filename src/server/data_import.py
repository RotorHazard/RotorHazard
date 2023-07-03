#
# Data import handlers
#

from RHUtils import catchLogExceptionsWrapper
from typing import List
from RHUI import UIField
from eventmanager import Evt
import logging

logger = logging.getLogger(__name__)

class DataImportManager():
    def __init__(self, rhapi, events):
        self._importers = {}

        self._rhapi = rhapi
        self._events = events

        events.trigger(Evt.DATA_IMPORT_INITIALIZE, {
            'register_fn': self.register_importer
            })

    def register_importer(self, importer):
        if isinstance(importer, DataImporter):
            if importer.name in self._importers:
                logger.warning('Overwriting data importer "{0}"'.format(importer['name']))

            self._importers[importer.name] = importer
        else:
            logger.warning('Invalid importer')

    @property
    def importers(self):
        return self._importers

    @catchLogExceptionsWrapper
    def run_import(self, importer_id, data, import_args=None):
        result = self._importers[importer_id].run_import(self._rhapi, data, import_args)

        if result:
            self._events.trigger(Evt.DATABASE_IMPORT)
        else:
            logger.warning("Failed importing data")
        return result

class DataImporter():
    def __init__(self, name, label, import_fn, default_args=None, settings:List[UIField]=None):
        self.name = name
        self.label = label
        self.import_fn = import_fn
        self.default_args = default_args
        self.settings = settings

    def run_import(self, rhapi, data, import_args=None):
        args = {**(self.default_args if self.default_args else {}), **(import_args if import_args else {})}
        return self.import_fn(rhapi, data, args)

