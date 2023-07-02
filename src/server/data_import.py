#
# Data import handlers
#

#
# name should be unique and acts as an identifier
# label becomes visible in the UI and becomes translatable
#

from RHUtils import catchLogExceptionsWrapper
from typing import List
from RHUI import UIField
from eventmanager import Evt
import logging

logger = logging.getLogger(__name__)

class DataImportManager():
    def __init__(self, RHAPI, Events):
        self._importers = {}

        self._rhapi = RHAPI

        Events.trigger(Evt.DATA_IMPORT_INITIALIZE, {
            'register_fn': self.registerImporter
            })

    def registerImporter(self, importer):
        if isinstance(importer, DataImporter):
            if importer.name in self._importers:
                logger.warning('Overwriting data importer "{0}"'.format(importer['name']))

            self._importers[importer.name] = importer
        else:
            logger.warning('Invalid importer')

    def hasImporter(self, importer_id):
        return importer_id in self._importers

    @property
    def importers(self):
        return self._importers

    @catchLogExceptionsWrapper
        return self._importers[importer_id].run_import(self._rhapi, data, import_args)

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
