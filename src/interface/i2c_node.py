'''RotorHazard I2C interface layer.'''
import logging
from monotonic import monotonic

from Node import Node
from RHInterface import READ_ADDRESS, READ_REVISION_CODE, MAX_RETRY_COUNT, \
                        READ_FW_VERSION, READ_FW_BUILDDATE, READ_FW_BUILDTIME, \
                        FW_TEXT_BLOCK_SIZE, validate_checksum, calculate_checksum, \
                        pack_16, unpack_16, READ_FW_PROCTYPE, SEND_STATUS_MESSAGE

logger = logging.getLogger(__name__)


class I2CNode(Node):
    def __init__(self, index, addr, i2c_helper):
        Node.__init__(self)
        self.index = index
        self.i2c_addr = addr
        self.i2c_helper = i2c_helper

    def read_block(self, interface, command, size, max_retries=MAX_RETRY_COUNT):
        '''
        Read i2c data given command, and data size.
        '''
        self.inc_read_block_count(interface)
        success = False
        retry_count = 0
        data = None
        while success is False and retry_count <= max_retries:
            try:
                def _read():
                    self.io_request = monotonic()
                    _data = self.i2c_helper.i2c.read_i2c_block_data(self.i2c_addr, command, size + 1)
                    self.io_response = monotonic()
                    if validate_checksum(_data):
                        return _data
                    else:
                        return None
                data = self.i2c_helper.with_i2c(_read)
                if data:
                    success = True
                    data = data[:-1]
                else:
                    # self.log('Invalid Checksum ({0}): {1}'.format(retry_count, data))
                    retry_count = retry_count + 1
                    if retry_count <= max_retries:
                        if retry_count > 1:  # don't log the occasional single retry
                            interface.log('Retry (checksum) in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(self.i2c_addr, command, size, retry_count, self.i2c_helper.i2c_timestamp))
                    else:
                        interface.log('Retry (checksum) limit reached in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(self.i2c_addr, command, size, retry_count, self.i2c_helper.i2c_timestamp))
                    self.inc_read_error_count(interface)
            except IOError as err:
                interface.log('Read Error: ' + str(err))
                self.i2c_helper.i2c_end()
                retry_count = retry_count + 1
                if retry_count <= max_retries:
                    if retry_count > 1:  # don't log the occasional single retry
                        interface.log('Retry (IOError) in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(self.i2c_addr, command, size, retry_count, self.i2c_helper.i2c_timestamp))
                else:
                    interface.log('Retry (IOError) limit reached in read_block:  addr={0} cmd={1} size={2} retry={3} ts={4}'.format(self.i2c_addr, command, size, retry_count, self.i2c_helper.i2c_timestamp))
                self.inc_read_error_count(interface)
        return data

    def write_block(self, interface, command, data):
        '''
        Write i2c data given command, and data.
        '''
        interface.inc_intf_write_block_count()
        success = False
        retry_count = 0
        data_with_checksum = data
        if self.api_level <= 19:
            data_with_checksum.append(command)
        data_with_checksum.append(calculate_checksum(data_with_checksum))
        while success is False and retry_count <= MAX_RETRY_COUNT:
            try:
                def _write():
                    # self.io_request = monotonic()
                    self.i2c_helper.i2c.write_i2c_block_data(self.i2c_addr, command, data_with_checksum)
                    # self.io_response = monotonic()
                    return True
                success = self.i2c_helper.with_i2c(_write)
                if success is None:
                    success = False
            except IOError as err:
                interface.log('Write Error: ' + str(err))
                self.i2c_helper.i2c_end()
                retry_count = retry_count + 1
                if retry_count <= MAX_RETRY_COUNT:
                    interface.log('Retry (IOError) in write_block:  addr={0} cmd={1} data={2} retry={3} ts={4}'.format(self.i2c_addr, command, data, retry_count, self.i2c_helper.i2c_timestamp))
                else:
                    interface.log('Retry (IOError) limit reached in write_block:  addr={0} cmd={1} data={2} retry={3} ts={4}'.format(self.i2c_addr, command, data, retry_count, self.i2c_helper.i2c_timestamp))
                interface.inc_intf_write_error_count()
        return success

    def jump_to_bootloader(self, interface):
        pass

    def read_firmware_version(self):
        # read firmware version string
        try:
            data = self.read_block(None, READ_FW_VERSION, FW_TEXT_BLOCK_SIZE, 2)
            self.firmware_version_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                          if data != None else None
        except Exception:
            logger.exception('Error fetching READ_FW_VERSION for I2C node')

    def read_firmware_proctype(self):
        # read firmware processor-type string
        try:
            data = self.read_block(None, READ_FW_PROCTYPE, FW_TEXT_BLOCK_SIZE, 2)
            self.firmware_proctype_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                         if data != None else None
        except Exception:
            logger.exception('Error fetching READ_FW_PROCTYPE for I2C node')

    def read_firmware_timestamp(self):
        # read firmware build date/time strings
        try:
            data = self.read_block(None, READ_FW_BUILDDATE, FW_TEXT_BLOCK_SIZE, 2)
            if data != None:
                self.firmware_timestamp_str = bytearray(data).decode("utf-8").rstrip('\0')
                data = self.read_block(None, READ_FW_BUILDTIME, FW_TEXT_BLOCK_SIZE, 2)
                if data != None:
                    self.firmware_timestamp_str += " " + bytearray(data).decode("utf-8").rstrip('\0')
            else:
                self.firmware_timestamp_str = None
        except Exception:
            logger.exception('Error fetching READ_FW_DATE/TIME for I2C node')

    def send_status_message(self, interface, msgTypeVal, msgDataVal):
        # send status message to node
        try:
            if self.api_level >= 35:
                data = ((msgTypeVal & 0xFF) << 8) | (msgDataVal & 0xFF)
#                logger.info(interface, 'Sending status message to I2C node {}: 0x{:04X}'.format(self.index+1, data))
                self.write_block(interface, SEND_STATUS_MESSAGE, pack_16(data))
                return True
        except Exception as ex:
            logger.error(interface, 'Error sending status message to I2C node {}: {}'.format(self.index+1, ex))
        return False


def discover(idxOffset, i2c_helper, isS32BPillFlag=False, *args, **kwargs):
    if not isS32BPillFlag:
        logger.info("Searching for I2C nodes...")
    nodes = []
    # Scans all i2c_addrs to populate nodes array
    i2c_addrs = [8, 10, 12, 14, 16, 18, 20, 22] # Software limited to 8 nodes
    for index, addr in enumerate(i2c_addrs):
        try:
            i2c_helper.i2c.read_i2c_block_data(addr, READ_ADDRESS, 1)
            node = I2CNode(index+idxOffset, addr, i2c_helper) # New node instance
            # read NODE_API_LEVEL and verification value:
            data = node.read_block(None, READ_REVISION_CODE, 2, 2)
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
                    logger.warning("Unable to verify revision code from node {}".format(index+idxOffset+1))
            else:
                logger.warning("Unable to read revision code from node {}".format(index+idxOffset+1))
            logger.info("...I2C node {} found at address {}, API_level={}{}{}{}".format(\
                        index+idxOffset+1, addr, node.api_level, fver_log_str, ftyp_log_str, ftim_log_str))
            nodes.append(node) # Add new node to RHInterface
        except IOError:
            if not isS32BPillFlag:
                logger.info("...No I2C node at address {0}".format(addr))
        i2c_helper.i2c_end()
        i2c_helper.i2c_sleep()
        if isS32BPillFlag and len(nodes) == 0:
            break  # if S32_BPill and first I2C node not found then stop trying
    return nodes
