'''Generic plugin manager'''

import logging
import importlib
import pkgutil
from UserList import UserList

logger = logging.getLogger(__name__)


def search_modules(prefix=None, suffix=None):
    plugin_modules = []
    for loader, name, ispkg in pkgutil.iter_modules():
        if (prefix is None or name.startswith(prefix+'_')) and (suffix is None or name.endswith('_'+suffix)):
            try:
                plugin_module = importlib.import_module(name)
                plugin_modules.append(plugin_module)
                logger.info('Loaded module {0}'.format(name))
            except ImportError:
                logger.debug('Module {0} not imported (not supported or may require additional dependencies)'.format(name))
    return plugin_modules

class Plugins(UserList):
    def __init__(self, prefix=None, suffix=None):
        UserList.__init__(self)
        self.prefix = prefix
        self.suffix = suffix

    def discover(self, includeOffset=False, *args, **kwargs):
        for plugin_module in search_modules(prefix = self.prefix, suffix = self.suffix):
            if includeOffset:
                kwargs['idxOffset'] = len(self.data)
            try:
                self.data.extend(plugin_module.discover(*args, **kwargs))
            except AttributeError as err:
                logger.error('Error loading plugin {0}: {1}'.format(plugin_module.__name__, err))
