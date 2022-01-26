'''RotorHazard I2C interface layer.'''
import logging

from .. import RHInterface as rhi

logger = logging.getLogger(__name__)


class I2CNodeManager(rhi.RHNodeManager):
    def __init__(self, i2c_addr, i2c_bus):
        super().__init__()
        self.i2c_addr = i2c_addr
        self.i2c_bus = i2c_bus
        self.addr = self.i2c_bus.url_of(self.i2c_addr)

    def _read_command(self, command, size):
        def _read():
            return self.i2c_bus.i2c.read_i2c_block_data(self.i2c_addr, command, size + 1)
        return self.i2c_bus.with_i2c(_read)

    def _write_command(self, command, data):
        def _write():
            self.i2c_bus.i2c.write_i2c_block_data(self.i2c_addr, command, data)
        self.i2c_bus.with_i2c(_write)


def discover(idxOffset, i2c_helper, i2c_addrs=[8, 10, 12, 14, 16, 18, 20, 22], *args, **kwargs):
    logger.info("Searching for I2C nodes...")
    node_managers = []
    # Scans provided i2c_addrs to populate nodes array
    next_index = idxOffset
    for i2c_bus in i2c_helper:
        for i2c_addr in i2c_addrs:
            node_manager = I2CNodeManager(i2c_addr, i2c_bus)
            try:
                node_addr = node_manager.read_address()
                if node_addr == i2c_addr:
                    if node_manager.discover_nodes(next_index):
                        logger.info('...{} I2C node(s) with API level {} found at address {}'.format(len(node_manager.nodes), node_manager.api_level, i2c_addr))
                        next_index += len(node_manager.nodes)
                        node_managers.append(node_manager)
                elif node_addr:
                    logger.error("Reported address {} does not match actual address {}".format(node_addr, i2c_addr))
            except IOError:
                logger.info("...No I2C nodes at address {}".format(i2c_addr))
            if len(node_managers) == 0:
                break  # if first I2C node not found then stop trying
    return node_managers
