'''RotorHazard I2C interface layer.'''
import logging

from .Node import Node
from interface import pack_8, unpack_8, pack_16, unpack_16, pack_32, unpack_32
from .RHInterface import READ_ADDRESS, READ_REVISION_CODE, \
                        READ_FW_VERSION, READ_FW_BUILDDATE, READ_FW_BUILDTIME, \
                        FW_TEXT_BLOCK_SIZE, \
                        READ_FW_PROCTYPE, SEND_STATUS_MESSAGE

logger = logging.getLogger(__name__)


class I2CNode(Node):
    def __init__(self, index, addr, i2c_bus):
        super().__init__()
        self.index = index
        self.i2c_addr = addr
        self.i2c_bus = i2c_bus

    @property
    def addr(self):
        return 'i2c:'+str(self.i2c_addr)

    def _read_command(self, command, size):
        def _read():
            return self.i2c_bus.i2c.read_i2c_block_data(self.i2c_addr, command, size + 1)
        return self.i2c_bus.with_i2c(_read)

    def _write_command(self, command, data):
        def _write():
            self.i2c_bus.i2c.write_i2c_block_data(self.i2c_addr, command, data)
        self.i2c_bus.with_i2c(_write)

    def read_firmware_version(self):
        # read firmware version string
        try:
            data = self.read_block_any(READ_FW_VERSION, FW_TEXT_BLOCK_SIZE, 2)
            self.firmware_version_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                          if data != None else None
        except Exception:
            logger.exception('Error fetching READ_FW_VERSION for I2C node')

    def read_firmware_proctype(self):
        # read firmware processor-type string
        try:
            data = self.read_block_any(READ_FW_PROCTYPE, FW_TEXT_BLOCK_SIZE, 2)
            self.firmware_proctype_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                         if data != None else None
        except Exception:
            logger.exception('Error fetching READ_FW_PROCTYPE for I2C node')

    def read_firmware_timestamp(self):
        # read firmware build date/time strings
        try:
            data = self.read_block_any(READ_FW_BUILDDATE, FW_TEXT_BLOCK_SIZE, 2)
            if data != None:
                self.firmware_timestamp_str = bytearray(data).decode("utf-8").rstrip('\0')
                data = self.read_block(READ_FW_BUILDTIME, FW_TEXT_BLOCK_SIZE, 2)
                if data != None:
                    self.firmware_timestamp_str += " " + bytearray(data).decode("utf-8").rstrip('\0')
            else:
                self.firmware_timestamp_str = None
        except Exception:
            logger.exception('Error fetching READ_FW_DATE/TIME for I2C node')

    def send_status_message(self, msgTypeVal, msgDataVal):
        # send status message to node
        try:
            if self.api_level >= 35:
                data = ((msgTypeVal & 0xFF) << 8) | (msgDataVal & 0xFF)
#                logger.warning('Sending status message to I2C node {}: 0x{:04X}'.format(self.index+1, data))
                self.write_block_any(SEND_STATUS_MESSAGE, pack_16(data))
                return True
        except Exception as ex:
            logger.warning('Error sending status message to I2C node {}: {}'.format(self.index+1, ex))
        return False


def discover(idxOffset, i2c_helper, *args, **kwargs):
    logger.info("Searching for I2C nodes...")
    nodes = []
    # Scans all i2c_addrs to populate nodes array
    i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
    for i2c_bus in i2c_helper:
        for index, addr in enumerate(i2c_addrs):
            try:
                i2c_bus.i2c.read_i2c_block_data(addr, READ_ADDRESS, 1)
                node = I2CNode(index+idxOffset, addr, i2c_bus) # New node instance
                # read NODE_API_LEVEL and verification value:
                data = node.read_block_any(READ_REVISION_CODE, 2, 2)
                rev_val = unpack_16(data) if data != None else None
                fver_log_str = ''
                ftyp_log_str = ''
                ftim_log_str = ''
                if rev_val:
                    if (rev_val >> 8) == 0x25:  # if verify passed (fn defined) then set API level
                        node.api_level = rev_val & 0xFF
                        if node.api_level >= 34:
                            node.read_firmware_version()
                            if node.firmware_version_str:
                                fver_log_str = ", fw_version=" + node.firmware_version_str
                            if node.api_level >= 35:
                                node.read_firmware_proctype()
                                if node.firmware_proctype_str:
                                    ftyp_log_str = ", fw_type=" + node.firmware_proctype_str
                            node.read_firmware_timestamp()
                            if node.firmware_timestamp_str:
                                ftim_log_str = ", fw_timestamp: " + node.firmware_timestamp_str
                    else:
                        logger.warn("Unable to verify revision code from node {}".format(index+idxOffset+1))
                else:
                    logger.warn("Unable to read revision code from node {}".format(index+idxOffset+1))
                logger.info("...I2C node {} found at address {}, API_level={}{}{}{}".format(\
                            index+idxOffset+1, addr, node.api_level, fver_log_str, ftyp_log_str, ftim_log_str))
                nodes.append(node) # Add new node to RHInterface
            except IOError:
                logger.info("...No I2C node at address {0}".format(addr))
            i2c_bus.i2c_end()
            i2c_bus.i2c_sleep()
            if len(nodes) == 0:
                break  # if first I2C node not found then stop trying
    return nodes
