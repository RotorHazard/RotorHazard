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
                logger.warning('Overwriting data importer "{0}"'.format(importer['name']))

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
    """Provides metadata and function linkage for importers.

    When an importer is run, the run_import method is called, which collates default and locally-provided arguments, then calls the import_fn.
    """
    def __init__(self, label, import_fn, default_args=None, settings:List[UIField]=None, name=None):
        """Constructor method

        :param label: User-facing text that appears in the RotorHazard frontend interface
        :type label: str
        :param import_fn: Function to run for formatting stage
        :type import_fn: callable
        :param default_args: Arguments passed to the import_fn when run, unless overridden by local arguments, defaults to None
        :type default_args: dict, optional
        :param settings: A list of paramters to provide to the user, defaults to None
        :type settings: List[UIField], optional
        :param name: Internal identifier (auto-generated from label if not provided), defaults to None
        :type name: _type_, optional
        """
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
        """Importer method

        :param rhapi: The :class:`RHAPI.RHAPI` class
        :type rhapi: RHAPI
        :param data: Data to import, provided by the user
        :type data: any
        :param import_args: Collated default and locally-provided arguments, defaults to None
        :type import_args: dict, optional
        :return: Result of :attr:`import_fn` if valid, else False
        :rtype: any|bool
        """
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

