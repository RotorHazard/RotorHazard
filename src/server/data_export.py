#
# Data export handlers
#

#
# Data exporters first collect data via their assembler function,
# then pass that data through the formatter function before output.
# PageCache is updated before export() is called and can be assumed accurate.
#
# name should be unique and acts as an identifier
# label becomes visible in the UI and becomes translatable
# formatter(data) should be used for final handling of file format
# assembler(RHData, PageCache, Language) collects relevant data from timer
#   before formatting.
#

from RHUtils import catchLogExceptionsWrapper
import logging

logger = logging.getLogger(__name__)

class DataExportManager():
    def __init__(self, RaceContext, Events):
        self._exporters = {}

        self._racecontext = RaceContext

        Events.trigger('Export_Initialize', {
            'registerFn': self.registerExporter
            })

    def registerExporter(self, exporter):
        if isinstance(exporter, DataExporter):
            if exporter.name in self._exporters:
                logger.warning('Overwriting data exporter "{0}"'.format(exporter['name']))

            self._exporters[exporter.name] = exporter
        else:
            logger.warning('Invalid exporter')

    def hasExporter(self, exporter_id):
        return exporter_id in self._exporters

    @property
    def exporters(self):
        return self._exporters

    @catchLogExceptionsWrapper
    def export(self, exporter_id):
        return self._exporters[exporter_id].export(self._racecontext)

class DataExporter():
    def __init__(self, name, label, formatter_fn, assembler_fn):
        self.name = name
        self.label = label
        self.formatter = formatter_fn
        self.assembler = assembler_fn

    def export(self, racecontext):
        data = self.assembler(racecontext)
        return self.formatter(data)
