#
# Data import handlers
#

from RHUtils import catchLogExceptionsWrapper, cleanVarName
from typing import List
from RHUI import UIField
from eventmanager import Evt
import logging

logger = logging.getLogger(__name__)

class DataImportManager():
    def __init__(self, rhapi, racecontext, events):
        self._importers = {}

        self._rhapi = rhapi
        self._racecontext = racecontext
        self._events = events

        events.trigger(Evt.DATA_IMPORT_INITIALIZE, {
            'register_fn': self.register_importer
            })

    def register_importer(self, importer):
        if isinstance(importer, DataImporter):
            if importer.name in self._importers:
                logger.warning('Overwriting data importer "{0}"'.format(importer.name))

            importer.add_racecontext(self._racecontext)

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
    def __init__(self, label, import_fn, default_args=None, settings:List[UIField]=None, name=None):
        if name is None:
            self.name = cleanVarName(label)
        else:
            self.name = name

        self.label = label
        self.import_fn = import_fn
        self.default_args = default_args
        self.settings = settings

    def add_racecontext(self, racecontext):
        self._racecontext = racecontext

    def run_import(self, rhapi, data, import_args=None):
        args = {**(self.default_args if self.default_args else {}), **(import_args if import_args else {})}
        result = self.import_fn(self, rhapi, data, args)
        if self.check_integrity():
            return result
        else:
            logger.error("Data import did not produce a valid database.")
            self._racecontext.rhdata.reset_all()
            return False

    def check_integrity(self):
        return self._racecontext.rhdata.check_integrity()
        
    def frequencysets_clear(self):
        self._racecontext.rhdata.clear_profiles()

    def raceformats_clear(self):
        self._racecontext.rhdata.clear_raceFormats()

