#
# Data export handlers
#

from RHUtils import catchLogExceptionsWrapper, cleanVarName
from eventmanager import Evt
import logging

logger = logging.getLogger(__name__)

class DataExportManager():
    def __init__(self, rhapi, events):
        self._exporters = {}

        self._rhapi = rhapi
        self._events = events

        events.trigger(Evt.DATA_EXPORT_INITIALIZE, {
            'register_fn': self.register_exporter
            })

    def register_exporter(self, exporter):
        if isinstance(exporter, DataExporter):
            if exporter.name in self._exporters:
                logger.warning('Overwriting data exporter "{0}"'.format(exporter['name']))

            self._exporters[exporter.name] = exporter
        else:
            logger.warning('Invalid exporter')

    @property
    def exporters(self):
        return self._exporters

    @catchLogExceptionsWrapper
    def export(self, exporter_id):
        result = self._exporters[exporter_id].export(self._rhapi)

        if result:
            self._events.trigger(Evt.DATABASE_EXPORT, result)
        else:
            logger.warning("Failed exporting data")
        return result

class DataExporter():
    """Provides metadata and function linkage for exporters.

    Exporters are run in two stages. First, the assembler pulls the data needed, then passes it to the formatter. In this way, a variety of assemblers can share a formatter, such as assembling pilot data, heat data, or race data and then passing it to be formatted as CSV or JSON.
    """ 
    def __init__(self, label, formatter_fn, assembler_fn, name=None):
        """Constructor method

        :param label: User-facing text that appears in the RotorHazard frontend interface
        :type label: str
        :param formatter_fn: Function to run for formatting stage
        :type formatter_fn: callable
        :param assembler_fn: Function to run for assembly stage
        :type assembler_fn: callable
        :param name: Internal identifier (auto-generated from label if not provided), defaults to None
        :type name: str, optional

        The formatter_fn receives the output of the assembler_fn.
        """
        if name is None:
            self.name = cleanVarName(label)
        else:
            self.name = name

        self.label = label
        self.formatter = formatter_fn
        self.assembler = assembler_fn

    def export(self, rhapi):
        """Export method

        :param rhapi: Receives :class:`RHAPI.RHAPI` as an argument so that it may access and prepare timer data as needed.
        :type rhapi: RHAPI
        :return: _description_
        :rtype: _type_
        """
        data = self.assembler(rhapi)
        return self.formatter(data)

