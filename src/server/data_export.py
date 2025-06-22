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
                logger.warning('Overwriting data exporter "{0}"'.format(exporter.name))

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
    def __init__(self, label, formatter_fn, assembler_fn, name=None):
        if name is None:
            self.name = cleanVarName(label)
        else:
            self.name = name

        self.label = label
        self.formatter = formatter_fn
        self.assembler = assembler_fn

    def export(self, rhapi):
        data = self.assembler(rhapi)
        return self.formatter(data)

