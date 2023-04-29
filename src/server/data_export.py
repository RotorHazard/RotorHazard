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

import logging

logger = logging.getLogger(__name__)

class DataExportManager():
    exporters = {}

    def __init__(self, RaceContext, Events):
        self._racecontext = RaceContext
        self.Events = Events

        self.Events.trigger('Export_Initialize', {
            'registerFn': self.registerExporter
            })

    def registerExporter(self, exporter):
        if hasattr(exporter, 'name'):
            if exporter.name in self.exporters:
                logger.warning('Overwriting data exporter "{0}"'.format(exporter['name']))

            self.exporters[exporter.name] = exporter
        else:
            logger.warning('Invalid exporter')

    def hasExporter(self, exporter_id):
        if exporter_id in self.exporters:
            return True
        return False

    def getExporters(self):
        return self.exporters

    def export(self, exporter_id):
        return self.exporters[exporter_id].export(self._racecontext)

class DataExporter():
    def __init__(self, name, label, formatterFn, assemblerFn):
        self.name = name
        self.label = label
        self.formatter = formatterFn
        self.assembler = assemblerFn

    def export(self, RHData, PageCache, Language):
        data = self.assembler(RHData, PageCache, Language)
        return self.formatter(data)
