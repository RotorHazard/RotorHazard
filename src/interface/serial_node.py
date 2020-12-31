'''RotorHazard hardware interface layer.'''
import logging
import serial # For serial comms
import gevent
import time
from monotonic import monotonic

from Node import Node
from RHInterface import READ_REVISION_CODE, READ_MULTINODE_COUNT, MAX_RETRY_COUNT, \
                        validate_checksum, calculate_checksum, pack_8, unpack_8, unpack_16, \
                        WRITE_CURNODE_INDEX, READ_CURNODE_INDEX, JUMP_TO_BOOTLOADER

BOOTLOADER_CHILL_TIME = 2 # Delay for USB to switch from bootloader to serial mode
SERIAL_BAUD_RATES = [921600, 115200]

logger = logging.getLogger(__name__)

node_io_rlock_obj = gevent.lock.RLock()  # semaphore lock for node I/O access


class SerialNode(Node):
    def __init__(self, index, node_serial_obj):
        Node.__init__(self)
        self.index = index
        self.serial = node_serial_obj
        
    def node_log(self, interface, message):
        if interface:
            interface.log(message)
        else:
            logger.info(message)

    #
    # Serial Common Functions
    #

    def read_block(self, interface, command, size, max_retries=MAX_RETRY_COUNT, check_multi_flag=True):
        '''
        Read serial data given command, and data size.
        '''
        with node_io_rlock_obj:  # only allow one greenlet at a time
            self.inc_read_block_count(interface)
            success = False
            retry_count = 0
            data = None
            while success is False and retry_count <= max_retries:
                if check_multi_flag:
                    if self.multi_node_index >= 0:
                        if not self.check_set_multi_node_index(interface):
                            break
                try:
                    self.io_request = monotonic()
                    self.serial.flushInput()
                    self.serial.write(bytearray([command]))
                    data = bytearray(self.serial.read(size + 1))
                    self.io_response = monotonic()
                    if validate_checksum(data):
                        if len(data) == size + 1:
                            success = True
                            data = data[:-1]
                        else:
                            retry_count = retry_count + 1
                            if check_multi_flag:  # log and count if regular query
                                if retry_count <= max_retries:
                                    self.node_log(interface, 'Retry (bad length) in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                                else:
                                    self.node_log(interface, 'Retry (bad length) limit reached in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                                self.inc_read_error_count(interface)
                                gevent.sleep(0.025)
                    else:
                        # self.log('Invalid Checksum ({0}): {1}'.format(retry_count, data))
                        retry_count = retry_count + 1
                        if check_multi_flag:  # log and count if regular query
                            if data and len(data) > 0:
                                if retry_count <= max_retries:
                                    self.node_log(interface, 'Retry (checksum) in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                                else:
                                    self.node_log(interface, 'Retry (checksum) limit reached in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                            else:
                                if retry_count <= max_retries:
                                    self.node_log(interface, 'Retry (no data) in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                                else:
                                    self.node_log(interface, 'Retry (no data) limit reached in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                            self.inc_read_error_count(interface)
                            gevent.sleep(0.025)
                except IOError as err:
                    self.node_log(interface, 'Read Error: ' + str(err))
                    retry_count = retry_count + 1
                    if check_multi_flag:  # log and count if regular query
                        if retry_count <= max_retries:
                            self.node_log(interface, 'Retry (IOError) in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                        else:
                            self.node_log(interface, 'Retry (IOError) limit reached in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                        self.inc_read_error_count(interface)
                        gevent.sleep(0.025)
            return data if success else None

    def write_block(self, interface, command, data, check_multi_flag=True):
        '''
        Write serial data given command, and data.
        '''
        with node_io_rlock_obj:  # only allow one greenlet at a time
            if interface:
                interface.inc_intf_write_block_count()
            success = False
            retry_count = 0
            data_with_checksum = bytearray()
            data_with_checksum.append(command)
            data_with_checksum.extend(data)
            data_with_checksum.append(calculate_checksum(data_with_checksum[1:]))
            while success is False and retry_count <= MAX_RETRY_COUNT:
                if check_multi_flag:
                    if self.multi_node_index >= 0:
                        if not self.check_set_multi_node_index(interface):
                            break
                try:
                    self.serial.write(data_with_checksum)
                    success = True
                except IOError as err:
                    self.node_log(interface, 'Write Error: ' + str(err))
                    retry_count = retry_count + 1
                    if retry_count <= MAX_RETRY_COUNT:
                        self.node_log(interface, 'Retry (IOError) in write_block:  port={0} cmd={1} data={2} retry={3}'.format(self.serial.port, command, data, retry_count))
                    else:
                        self.node_log(interface, 'Retry (IOError) limit reached in write_block:  port={0} cmd={1} data={2} retry={3}'.format(self.serial.port, command, data, retry_count))
                    if interface:
                        interface.inc_intf_write_error_count()
                    gevent.sleep(0.025)
            return success

    def check_set_multi_node_index(self, interface):
        # check if need to set different node index on multi-node processor and set if needed
        if self.multi_node_index == self.multi_curnode_index_holder[0]:
            return True
        success = False
        chk_retry_count = 0
        out_value = None
        while success is False:
            if self.write_block(interface, WRITE_CURNODE_INDEX, pack_8(self.multi_node_index), False):
                data = self.read_block(interface, READ_CURNODE_INDEX, 1, 0, False)
                out_value = unpack_8(data) if data != None else None
            if out_value == self.multi_node_index:
                success = True
            else:
                chk_retry_count = chk_retry_count + 1
                self.inc_read_error_count(interface)
                if chk_retry_count <= MAX_RETRY_COUNT*5:
                    self.node_log(interface, 'Error setting WRITE_CURNODE_INDEX, old={0}, new={1}, idx={2}, retry={3}'.\
                                  format(self.multi_curnode_index_holder[0], self.multi_node_index, self.index, chk_retry_count))
                    gevent.sleep(0.025)
                else:
                    self.node_log(interface, 'Error setting WRITE_CURNODE_INDEX, retry limit reached, old={0}, new={1}, idx={2}, retry={3}'.\
                                  format(self.multi_curnode_index_holder[0], self.multi_node_index, self.index, chk_retry_count))
                    break
        if success:
            self.multi_curnode_index_holder[0] = self.multi_node_index
        return success

    def jump_to_bootloader(self, interface):
        try:
            if self.api_level >= 32:
                self.node_log(interface, 'Sending JUMP_TO_BOOTLOADER message to serial node {0}'.format(self.index+1))
                self.write_block(interface, JUMP_TO_BOOTLOADER, pack_8(0), False)
                self.serial.flushInput()
                time.sleep(0.1)
                self.serial.flushInput()
                self.serial.flushOutput()
                self.serial.close()
        except Exception as ex:
            self.node_log(interface, 'Error sending JUMP_TO_BOOTLOADER message to serial node {0}: {1}'.format(self.index+1, ex))


def discover(idxOffset, config, *args, **kwargs):
    nodes = []
    config_ser_ports = getattr(config, 'SERIAL_PORTS', None)
    if config_ser_ports:
        logger.info("Searching for serial nodes...")
        for index, comm in enumerate(config_ser_ports):
            rev_val = None
            baud_idx = 0
            while rev_val == None and baud_idx < len(SERIAL_BAUD_RATES):
                node_serial_obj = serial.Serial(port=comm, baudrate=SERIAL_BAUD_RATES[baud_idx], timeout=0.25)
                node_serial_obj.setDTR(0)  # clear in case line is tied to node-processor reset
                if baud_idx > 0:
                    gevent.sleep(BOOTLOADER_CHILL_TIME)  # delay needed for Arduino USB
                node = SerialNode(index+idxOffset, node_serial_obj)
                multi_count = 1
                try:               # handle serial multi-node processor
                    data = node.read_block(None, READ_REVISION_CODE, 2, 2, False)
                    rev_val = unpack_16(data) if data != None else None
                    if rev_val and (rev_val >> 8) == 0x25:
                        if (rev_val & 0xFF) >= 32:  # check node API level
                            data = node.read_block(None, READ_MULTINODE_COUNT, 1, 2, False)
                            multi_count = unpack_8(data) if data != None else None
                        if multi_count is None or multi_count < 1 or multi_count > 32:
                            logger.error('Bad READ_MULTINODE_COUNT value fetched from serial node:  ' + str(multi_count))
                            multi_count = 1
                except Exception:
                    multi_count = 1
                    logger.exception('Error fetching READ_MULTINODE_COUNT for serial node')
                if rev_val == None:
                    node_serial_obj.close()
                    baud_idx += 1
            if rev_val:
                if multi_count <= 1:
                    logger.info("...Serial node {0} found at port {1}, baudrate={2}".format(\
                                index+idxOffset+1, node.serial.name, node.serial.baudrate))
                    nodes.append(node)
                else:
                    node.multi_node_index = 0
                    curnode_index_holder = [-1]  # tracker for index of current node for processor
                    node.multi_curnode_index_holder = curnode_index_holder
                    logger.info("...Serial (multi) node {0} found at port {1}, baudrate={2}".format(\
                                index+idxOffset+1, node.serial.name, node.serial.baudrate))
                    nodes.append(node)
                    for nIdx in range(1, multi_count):
                        idxOffset += 1
                        node = SerialNode(index+idxOffset, node_serial_obj)
                        node.multi_node_index = nIdx
                        node.multi_curnode_index_holder = curnode_index_holder
                        logger.info("...Serial (multi) node {0} found at port {1}, baudrate={2}".format(\
                                    index+idxOffset+1, node.serial.name, node.serial.baudrate))
                        nodes.append(node)
            else:
                logger.error('Unable to fetch revision code for serial node at "{0}"'.format(comm))
    return nodes
