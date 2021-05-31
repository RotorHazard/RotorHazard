'''RotorHazard I2C interface layer.'''
import logging

from .Node import Node
from . import RHInterface as rhi

logger = logging.getLogger(__name__)


class I2CNode(Node):
    def __init__(self, index, addr, i2c_bus):
        super().__init__(index=index)
        self.i2c_addr = addr
        self.i2c_bus = i2c_bus


    @property
    def addr(self):
        return self.i2c_bus.url_of(self.i2c_addr)


    def _create(self, index):
        return I2CNode(index, self.i2c_addr, self.i2c_bus)


    def _read_command(self, command, size):
        def _read():
            return self.i2c_bus.i2c.read_i2c_block_data(self.i2c_addr, command, size + 1)
        return self.i2c_bus.with_i2c(_read)


    def _write_command(self, command, data):
        def _write():
            self.i2c_bus.i2c.write_i2c_block_data(self.i2c_addr, command, data)
        self.i2c_bus.with_i2c(_write)


def discover(idxOffset, i2c_helper, *args, **kwargs):
    logger.info("Searching for I2C nodes...")
    nodes = []
    # Scans all i2c_addrs to populate nodes array
    i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
    next_index = idxOffset
    for i2c_bus in i2c_helper:
        for addr in i2c_addrs:
            node = I2CNode(next_index, addr, i2c_bus)
            try:
                node_addr = rhi.read_address(node)
                if node_addr == addr:
                    logger.info("...I2C node {} found at address {}".format(node, addr))
                    multi_nodes = rhi.build_nodes(node)
                    next_index += len(multi_nodes)
                    nodes.extend(multi_nodes)
                elif node_addr:
                    logger.error("Reported address {} does not match actual address {}".format(node_addr, addr))
            except IOError:
                logger.info("...No I2C node at address {}".format(addr))
            if len(nodes) == 0:
                break  # if first I2C node not found then stop trying
    return nodes
