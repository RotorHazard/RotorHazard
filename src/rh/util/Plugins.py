'''Generic plugin manager'''

import logging
import importlib
import pkgutil
from collections import UserList

logger = logging.getLogger(__name__)

def search_modules(pkg, prefix=None, suffix=None):
    plugin_modules = []
    pkg_prefix = pkg.__name__ + '.'
    for loader, name, ispkg in pkgutil.iter_modules(pkg.__path__):
        if (prefix is None or name.startswith(prefix+'_')) and (suffix is None or name.endswith('_'+suffix)):
            try:
                plugin_module = importlib.import_module(pkg_prefix+name)
                plugin_modules.append(plugin_module)
                logger.info('Loaded module {0}'.format(name))
            except ImportError as ex:
                logger.debug('Module {0} not imported (not supported or may require additional dependencies)\n\t{1}'.format(name, ex))
    return plugin_modules


class Plugins(UserList):
    def __init__(self, prefix=None, suffix=None):
        UserList.__init__(self)
        self.prefix = prefix
        self.suffix = suffix

    def discover(self, pkg, includeOffset=False, *args, **kwargs):
        for plugin_module in search_modules(pkg, prefix = self.prefix, suffix = self.suffix):
            if includeOffset:
                kwargs['idxOffset'] = len(self.data)
            try:
                self.data.extend(plugin_module.discover(*args, **kwargs))
            except TypeError as ex:
                logger.debug('Plugin {0} not loaded (not supported - required arguments are not available)\n\t{1}'.format(plugin_module.__name__, ex))
            except AttributeError as err:
                logger.error('Error loading plugin {0}: {1}'.format(plugin_module.__name__, err))
        self._post_discover()

    def _post_discover(self):
        pass
