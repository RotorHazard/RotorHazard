'''RotorHazard hardware interface layer.'''
import logging
import os
import serial # For serial comms
import gevent
import time
from time import monotonic

from Node import Node
from RHInterface import READ_REVISION_CODE, READ_MULTINODE_COUNT, MAX_RETRY_COUNT, \
                        validate_checksum, calculate_checksum, pack_8, pack_16, unpack_8, unpack_16, \
                        WRITE_CURNODE_INDEX, READ_CURNODE_INDEX, READ_NODE_SLOTIDX, \
                        READ_FW_VERSION, READ_FW_BUILDDATE, READ_FW_BUILDTIME, FW_TEXT_BLOCK_SIZE, \
                        JUMP_TO_BOOTLOADER, READ_FW_PROCTYPE, SEND_STATUS_MESSAGE

BOOTLOADER_CHILL_TIME = 2 # Delay for USB to switch from bootloader to serial mode
SERIAL_BAUD_RATES = [921600, 115200]
SYS_DEV_DIR_PATH = "/dev/"
DEF_S32BPILL_SERIAL_PORTS = ["ttyAMA0", "serial0"]
PORT_DISCOVERY_TIMEOUT = 10.0  # Maximum seconds to spend trying to discover a node on each port

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

    def read_block(self, interface, command, size, max_retries=MAX_RETRY_COUNT, check_multi_flag=True, deadline=None):
        '''
        Read serial data given command, and data size.
        deadline: optional monotonic() time after which to abort
        '''
        with node_io_rlock_obj:  # only allow one greenlet at a time
            self.inc_read_block_count(interface)
            success = False
            retry_count = 0
            data = None
            while success is False and retry_count <= max_retries:
                # Check if we've exceeded the deadline
                if deadline is not None and monotonic() > deadline:
                    return None
                if check_multi_flag:
                    if self.multi_node_index >= 0:
                        if not self.check_set_multi_node_index(interface):
                            break
                try:
                    self.io_request = monotonic()
                    self.serial.flushInput()
                    gevent.sleep(0)  # Yield to allow gevent to process other tasks
                    self.serial.write(bytearray([command]))
                    gevent.sleep(0)  # Yield again after write
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
                except (IOError, serial.SerialTimeoutException) as err:
                    retry_count = retry_count + 1
                    if check_multi_flag:  # log and count if regular query
                        if retry_count <= max_retries:
                            self.node_log(interface, 'Retry (IOError/Timeout) in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
                        else:
                            self.node_log(interface, 'Retry (IOError/Timeout) limit reached in read_block:  port={0} cmd={1} size={2} retry={3}'.format(self.serial.port, command, size, retry_count))
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

    def send_status_message(self, interface, msgTypeVal, msgDataVal):
        # send status message to node
        try:
            if self.api_level >= 35:
                data = ((msgTypeVal & 0xFF) << 8) | (msgDataVal & 0xFF)
#                self.node_log(interface, 'Sending status message to serial node {}: 0x{:04X}'.format(self.index+1, data))
                self.write_block(interface, SEND_STATUS_MESSAGE, pack_16(data), False)
                return True
        except Exception as ex:
            self.node_log(interface, 'Error sending status message to serial node {}: {}'.format(self.index+1, ex))
        return False

    def read_node_slot_index(self):
        # read node slot index (physical slot position of node on S32_BPill PCB)
        try:
            data = self.read_block(None, READ_NODE_SLOTIDX, 1, 1)
            self.multi_node_slot_index = unpack_8(data) if data else -1
        except Exception:
            self.multi_node_slot_index = -1

    def read_firmware_version(self):
        # read firmware version string
        try:
            data = self.read_block(None, READ_FW_VERSION, FW_TEXT_BLOCK_SIZE, 2, False)
            self.firmware_version_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                          if data != None else None
        except Exception:
            logger.exception('Error fetching READ_FW_VERSION for serial node')

    def read_firmware_proctype(self):
        # read firmware processor-type string
        try:
            data = self.read_block(None, READ_FW_PROCTYPE, FW_TEXT_BLOCK_SIZE, 2, False)
            self.firmware_proctype_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                         if data != None else None
        except Exception:
            logger.exception('Error fetching READ_FW_PROCTYPE for serial node')

    def read_firmware_timestamp(self):
        # read firmware build date/time strings
        try:
            data = self.read_block(None, READ_FW_BUILDDATE, FW_TEXT_BLOCK_SIZE, 2, False)
            if data != None:
                self.firmware_timestamp_str = bytearray(data).decode("utf-8").rstrip('\0')
                data = self.read_block(None, READ_FW_BUILDTIME, FW_TEXT_BLOCK_SIZE, 2, False)
                if data != None:
                    self.firmware_timestamp_str += " " + bytearray(data).decode("utf-8").rstrip('\0')
            else:
                self.firmware_timestamp_str = None
        except Exception:
            logger.exception('Error fetching READ_FW_DATE/TIME for serial node')


def discover(idxOffset, config, isS32BPillFlag=False, *args, **kwargs):
    logger.info("=== Starting serial node discovery ===")
    nodes = []
    config_ser_ports = config.get_item('GENERAL', 'SERIAL_PORTS')
    if config_ser_ports:
        logger.info("Configured serial ports: {0}".format(config_ser_ports))
    if isS32BPillFlag and len(config_ser_ports) == 0:
        try:    # if "/dev/ttyAMA0" exist then use it, otherwise use "/dev/serial0"
            def_port = SYS_DEV_DIR_PATH + (DEF_S32BPILL_SERIAL_PORTS[0] \
                                if DEF_S32BPILL_SERIAL_PORTS[0] in os.listdir(SYS_DEV_DIR_PATH) \
                                else DEF_S32BPILL_SERIAL_PORTS[1])
            config_ser_ports.append(def_port)
            logger.debug("Using default serial port ('{}') for S32_BPill board".format(def_port))
        except:
            pass
    if config_ser_ports:
        node_serial_obj = None
        for index, comm in enumerate(config_ser_ports):
            logger.info("Attempting to discover serial node on port '{0}'".format(comm))
            port_start_time = time.time()  # Start timeout timer for this port
            rev_val = None
            baud_idx = 0
            while (not rev_val) and baud_idx < len(SERIAL_BAUD_RATES):
                # Check if we've exceeded the per-port timeout
                if time.time() - port_start_time > PORT_DISCOVERY_TIMEOUT:
                    logger.warning("Discovery timeout ({0}s) exceeded for port '{1}' - moving to next port".format(PORT_DISCOVERY_TIMEOUT, comm))
                    break
                
                logger.info("Trying baudrate {0} on port '{1}'".format(SERIAL_BAUD_RATES[baud_idx], comm))
                attempt_count = 0
                max_attempts = 3
                # if opening port fails then do retries with short delays
                while (not rev_val) and attempt_count < max_attempts:
                    # Check timeout in inner loop too
                    if time.time() - port_start_time > PORT_DISCOVERY_TIMEOUT:
                        logger.warning("Discovery timeout exceeded during baudrate retry - aborting port '{0}'".format(comm))
                        break
                    
                    attempt_count += 1
                    # Moderate timeout (0.25s read, 0.5s write) - fast enough to detect non-responsive devices but allows real devices time to respond
                    node_serial_obj = serial.Serial(port=None, baudrate=SERIAL_BAUD_RATES[baud_idx], timeout=0.25, write_timeout=0.5)
                    node_serial_obj.setDTR(0)  # clear in case line is tied to node-processor reset
                    node_serial_obj.setRTS(0)
                    node_serial_obj.setPort(comm)
                    node_serial_obj.open()  # open port (now that DTR is configured for no change)
                    # Only delay on retry attempts, not the first attempt
                    if attempt_count > 1:
                        delay_secs = 0.1  # Short 100ms delay between retries
                        logger.debug("Delaying {} secs before retry attempt".format(delay_secs))
                        gevent.sleep(delay_secs)
                    node = SerialNode(index+idxOffset, node_serial_obj)
                    multi_count = 1
                    try:               # handle serial multi-node processor
                        # read NODE_API_LEVEL and verification value with timeout protection
                        logger.info("Attempting to read revision code from serial node at port '{0}' (baudrate={1})...".format(comm, SERIAL_BAUD_RATES[baud_idx]))
                        
                        # Set a 3-second deadline for this read (allows time for device to respond while preventing infinite hangs)
                        read_deadline = monotonic() + 3.0
                        data = node.read_block(None, READ_REVISION_CODE, 2, 2, False, deadline=read_deadline)
                        if data is None:
                            logger.warning("Timeout reading revision code from port '{0}' at baudrate {1}".format(comm, SERIAL_BAUD_RATES[baud_idx]))
                        
                        rev_val = unpack_16(data) if data != None else None
                        if rev_val:
                            logger.debug("Received revision code: 0x{0:04X}".format(rev_val))
                        if rev_val and (rev_val >> 8) == 0x25:
                            if (rev_val & 0xFF) >= 32:  # check node API level
                                # Set a 3-second deadline for multinode count read
                                read_deadline = monotonic() + 3.0
                                data = node.read_block(None, READ_MULTINODE_COUNT, 1, 2, False, deadline=read_deadline)
                                multi_count = unpack_8(data) if data != None else None
                                if multi_count is None:
                                    logger.warning("Timeout reading multinode count from port '{0}'".format(comm))
                                    multi_count = 1  # Assume single node on timeout
                            if multi_count is None or multi_count < 0 or multi_count > 32:
                                logger.error('Bad READ_MULTINODE_COUNT value fetched from serial node:  ' + str(multi_count))
                                multi_count = 1
                            elif multi_count == 0:
                                logger.debug('Fetched READ_MULTINODE_COUNT value of zero from serial node (no modules detected)')
                                multi_count = 0
                    except Exception:
                        multi_count = 1
                        logger.exception('Error fetching READ_MULTINODE_COUNT for serial node')
                    # Don't close the port during retries - closing a non-responsive USB CDC device
                    # can block for 30+ seconds. Just leave it open; if discovery fails, we'll skip
                    # the close entirely to avoid blocking.
                if (not rev_val):  # if connection attempt failed then retry with alternate baud rate
                    baud_idx += 1
            if rev_val:
                api_level = rev_val & 0xFF
                node.api_level = api_level
                node_version_str = None
                node_timestamp_str = None
                fver_log_str = ''
                ftyp_log_str = ''
                ftim_log_str = ''
                if api_level >= 34:  # read firmware version and build timestamp strings
                    node.read_firmware_version()
                    if node.firmware_version_str:
                        node_version_str = node.firmware_version_str
                        fver_log_str = ", fw_version=" + node.firmware_version_str
                        if node.api_level >= 35:
                            node.read_firmware_proctype()
                            if node.firmware_proctype_str:
                                ftyp_log_str = ", fw_type=" + node.firmware_proctype_str
                    node.read_firmware_timestamp()
                    if node.firmware_timestamp_str:
                        node_timestamp_str = node.firmware_timestamp_str
                        ftim_log_str = ", fw_timestamp: " + node.firmware_timestamp_str
                if multi_count <= 1:
                    if multi_count > 0:
                        logger.info("Serial node {} found at port '{}', API_level={}, baudrate={}{}{}{}".format(\
                                    index+idxOffset+1, node.serial.name, api_level, node.serial.baudrate, \
                                    fver_log_str, ftyp_log_str, ftim_log_str))
                        nodes.append(node)
                    else:
                        if 'set_info_node_obj_fn' in kwargs:
                            kwargs['set_info_node_obj_fn'](node)  # set 'info_node_obj' in RHInterface
                        logger.info("Serial node (with zero modules) found at port '{}', API_level={}, baudrate={}{}{}{}".format(\
                                    node.serial.name, api_level, node.serial.baudrate, \
                                    fver_log_str, ftyp_log_str, ftim_log_str))
                else:
                    logger.info("Serial multi-node found at port '{}', count={}, API_level={}, baudrate={}{}{}{}".\
                                format(node.serial.name, multi_count, api_level, node.serial.baudrate, \
                                fver_log_str, ftyp_log_str, ftim_log_str))
                    node.multi_node_index = 0
                    curnode_index_holder = [-1]  # tracker for index of current node for processor
                    node.multi_curnode_index_holder = curnode_index_holder
                    node.read_node_slot_index()
                    logger.debug("Serial (multi) node {} (slot={}) added for port '{}'".format(\
                                 index+idxOffset+1, node.multi_node_slot_index+1, node.serial.name))
                    nodes.append(node)
                    slots_str = str(node.multi_node_slot_index+1)
                    for nIdx in range(1, multi_count):
                        idxOffset += 1
                        node = SerialNode(index+idxOffset, node_serial_obj)
                        node.multi_node_index = nIdx
                        node.multi_curnode_index_holder = curnode_index_holder
                        node.api_level = api_level
                        node.firmware_version_str = node_version_str
                        node.firmware_timestamp_str = node_timestamp_str
                        node.read_node_slot_index()
                        logger.debug("Serial (multi) node {} (slot={}) added for port '{}'".format(\
                                     index+idxOffset+1, node.multi_node_slot_index+1, node.serial.name))
                        nodes.append(node)
                        slots_str += ' ' + str(node.multi_node_slot_index+1)
                    logger.info("Receiver modules found at slot positions: " + slots_str)
            else:
                logger.warning('Unable to fetch revision code for serial node at "{0}" - device not responding or wrong mode'.format(comm))
                logger.warning('Skipping port "{0}" and continuing with server startup...'.format(comm))
            
            # Always close serial port if we didn't find a valid node
            if not rev_val and node_serial_obj:
                # Don't close non-responsive serial ports - close() can block for 30+ seconds!
                # Just abandon the port and let the OS clean it up when the process exits.
                # The port will be released and available for other processes.
                logger.debug("Skipping close() on non-responsive port '{0}' to avoid blocking".format(comm))
                node_serial_obj = None
    logger.info("=== Serial node discovery complete: found {0} node(s) ===".format(len(nodes)))
    return nodes
