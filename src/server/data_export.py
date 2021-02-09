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
# assembler(Database, PageCache) collects relevant data from timer
#   before formatting.
#

import logging
from six.moves import UserDict
from Plugins import Plugins

class dataExportManager():
    exporters = {}

    def __init__(self):
        self.readPlugins()

    def readPlugins(self):
        exporter_plugins = Plugins(prefix='data_export')
        exporter_plugins.discover()

        for exporter in exporter_plugins:
            self.registerExporter(exporter)

    def registerExporter(self, exporter):
        if 'name' in exporter:
            if exporter['name'] in self.exporters:
                logger.warning('Overwriting data exporter "{0}"'.format(exporter['name']))

            self.exporters[exporter['name']] = exporter
        else:
            logger.warning('Invalid exporter')

    def isExporter(self, exporter_id):
        if exporter_id in self.exporters:
            return True
        return False

    def getExporters(self):
        return self.exporters

    def export(self, exporter_id, Database, PageCache):
        data = self.exporters[exporter_id]['assembler'](Database, PageCache)
        return self.exporters[exporter_id]['formatter'](data)

class DataExporter(UserDict):
    def __init__(self, name, label, formatterFn, assemblerFn, args=None):
        UserDict.__init__(self, {
            "name": name,
            "label": label,
            "formatter": formatterFn,
            "assembler": assemblerFn
        })
