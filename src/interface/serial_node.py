'''RotorHazard hardware interface layer.'''
import logging
import serial # For serial comms
import gevent
import time

from .Node import Node, SharedIOLine
from interface import pack_8, unpack_8, pack_16, unpack_16, pack_32, unpack_32
from .RHInterface import READ_REVISION_CODE, READ_MULTINODE_COUNT, \
                        READ_NODE_SLOTIDX, \
                        WRITE_CURNODE_INDEX, READ_CURNODE_INDEX, \
                        READ_FW_VERSION, READ_FW_BUILDDATE, READ_FW_BUILDTIME, FW_TEXT_BLOCK_SIZE, \
                        JUMP_TO_BOOTLOADER, READ_FW_PROCTYPE, SEND_STATUS_MESSAGE

BOOTLOADER_CHILL_TIME = 2 # Delay for USB to switch from bootloader to serial mode
SERIAL_BAUD_RATES = [921600, 500000, 115200]
DEF_S32BPILL_SERIAL_PORT = "/dev/serial0"

logger = logging.getLogger(__name__)


class SerialNode(Node):
    def __init__(self, index, node_serial_obj):
        super().__init__()
        self.index = index
        self.serial_io = node_serial_obj

    @property
    def addr(self):
        return 'serial:'+self.serial_io.port

    def _read_command(self, command, size):
        self.serial_io.flushInput()
        self.serial_io.write(bytearray([command]))
        return bytearray(self.serial_io.read(size + 1))

    def _write_command(self, command, data):
        data_with_cmd = bytearray()
        data_with_cmd.append(command)
        data_with_cmd.extend(data)
        self.serial_io.write(data_with_cmd)

    def jump_to_bootloader(self):
        try:
            if self.api_level >= 32:
                logger.info('Sending JUMP_TO_BOOTLOADER message to serial node {0}'.format(self))
                self.write_block_any(JUMP_TO_BOOTLOADER, pack_8(0))
                self.serial_io.flushInput()
                time.sleep(0.1)
                self.serial_io.flushInput()
                self.serial_io.flushOutput()
                self.serial_io.close()
        except Exception as ex:
            logger.error('Error sending JUMP_TO_BOOTLOADER message to serial node {0}: {1}'.format(self, ex))

    def send_status_message(self, msgTypeVal, msgDataVal):
        # send status message to node
        try:
            if self.api_level >= 35:
                data = ((msgTypeVal & 0xFF) << 8) | (msgDataVal & 0xFF)
#                logger.info('Sending status message to serial node {}: 0x{:04X}'.format(self, data))
                self.write_block_any(SEND_STATUS_MESSAGE, pack_16(data))
                return True
        except Exception as ex:
            logger.error('Error sending status message to serial node {}: {}'.format(self, ex))
        return False

    def read_node_slot_index(self):
        # read node slot index (physical slot position of node on S32_BPill PCB)
        try:
            self.multi_node_slot_index = self.get_value_8(READ_NODE_SLOTIDX)
        except Exception:
            self.multi_node_slot_index = None

    def read_firmware_version(self):
        # read firmware version string
        try:
            data = self.read_block_any(READ_FW_VERSION, FW_TEXT_BLOCK_SIZE, 2)
            self.firmware_version_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                          if data != None else None
        except Exception:
            logger.exception('Error fetching READ_FW_VERSION for serial node')

    def read_firmware_proctype(self):
        # read firmware processor-type string
        try:
            data = self.read_block_any(READ_FW_PROCTYPE, FW_TEXT_BLOCK_SIZE, 2)
            self.firmware_proctype_str = bytearray(data).decode("utf-8").rstrip('\0') \
                                         if data != None else None
        except Exception:
            logger.exception('Error fetching READ_FW_PROCTYPE for serial node')

    def read_firmware_timestamp(self):
        # read firmware build date/time strings
        try:
            data = self.read_block_any(READ_FW_BUILDDATE, FW_TEXT_BLOCK_SIZE, 2)
            if data != None:
                self.firmware_timestamp_str = bytearray(data).decode("utf-8").rstrip('\0')
                data = self.read_block_any(READ_FW_BUILDTIME, FW_TEXT_BLOCK_SIZE, 2)
                if data != None:
                    self.firmware_timestamp_str += " " + bytearray(data).decode("utf-8").rstrip('\0')
            else:
                self.firmware_timestamp_str = None
        except Exception:
            logger.exception('Error fetching READ_FW_DATE/TIME for serial node')


def discover(idxOffset, config, isS32BPillFlag=False, *args, **kwargs):
    nodes = []
    config_ser_ports = getattr(config, 'SERIAL_PORTS', [])
    if isS32BPillFlag and len(config_ser_ports) == 0:
        config_ser_ports.append(DEF_S32BPILL_SERIAL_PORT)
        logger.debug("Using default serial port ('{}') for S32_BPill board".format(DEF_S32BPILL_SERIAL_PORT))
    if config_ser_ports:
        for index, comm in enumerate(config_ser_ports):
            rev_val = None
            baud_idx = 0
            while rev_val == None and baud_idx < len(SERIAL_BAUD_RATES):
                baudrate = SERIAL_BAUD_RATES[baud_idx]
                logger.info("Trying {} with baud rate {}".format(comm, baudrate))
                node_serial_obj = serial.Serial(port=None, baudrate=baudrate, timeout=0.25)
                node_serial_obj.setDTR(0)  # clear in case line is tied to node-processor reset
                node_serial_obj.setRTS(0)
                node_serial_obj.setPort(comm)
                node_serial_obj.open()  # open port (now that DTR is configured for no change)
                if baud_idx > 0:
                    gevent.sleep(BOOTLOADER_CHILL_TIME)  # delay needed for Arduino USB
                node = SerialNode(index+idxOffset, node_serial_obj)
                multi_count = 1
                try:               # handle serial multi-node processor
                    # read NODE_API_LEVEL and verification value:
                    data = node.read_block_any(READ_REVISION_CODE, 2, 2)
                    rev_val = unpack_16(data) if data != None else None
                    if rev_val and (rev_val >> 8) == 0x25:
                        if (rev_val & 0xFF) >= 32:  # check node API level
                            data = node.read_block_any(READ_MULTINODE_COUNT, 1, 2)
                            multi_count = unpack_8(data) if data != None else None
                        if multi_count is None or multi_count < 0 or multi_count > 32:
                            logger.error('Bad READ_MULTINODE_COUNT value fetched from serial node:  ' + str(multi_count))
                            multi_count = 1
                        elif multi_count == 0:
                            logger.warning('Fetched READ_MULTINODE_COUNT value of zero from serial node (no modules detected)')
                            multi_count = 0
                except Exception:
                    multi_count = 1
                    logger.exception('Error fetching READ_MULTINODE_COUNT for serial node')
                if rev_val == None:
                    node_serial_obj.close()
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
                                    node, node.serial_io.name, api_level, node.serial_io.baudrate, \
                                    fver_log_str, ftyp_log_str, ftim_log_str))
                        nodes.append(node)
                    else:
                        logger.info("Serial node (with zero modules) found at port '{}', API_level={}, baudrate={}{}{}{}".format(\
                                    node.serial_io.name, api_level, node.serial_io.baudrate, \
                                    fver_log_str, ftyp_log_str, ftim_log_str))
                else:
                    logger.info("Serial multi-node found at port '{}', count={}, API_level={}, baudrate={}{}{}{}".\
                                format(node.serial_io.name, multi_count, api_level, node.serial_io.baudrate, \
                                fver_log_str, ftyp_log_str, ftim_log_str))
                    node.multi_node_index = 0
                    io_line = SharedIOLine(WRITE_CURNODE_INDEX, READ_CURNODE_INDEX)
                    node.io_line = io_line
                    node.read_node_slot_index()
                    logger.debug("Serial (multi) node {} (slot={}) added for port '{}'".format(\
                                 node, node.multi_node_slot_index+1, node.serial_io.name))
                    nodes.append(node)
                    for nIdx in range(1, multi_count):
                        idxOffset += 1
                        node = SerialNode(index+idxOffset, node_serial_obj)
                        node.multi_node_index = nIdx
                        node.io_line = io_line
                        node.api_level = api_level
                        node.firmware_version_str = node_version_str
                        node.firmware_timestamp_str = node_timestamp_str
                        node.read_node_slot_index()
                        logger.debug("Serial (multi) node {} (slot={}) added for port '{}'".format(\
                                     node, node.multi_node_slot_index+1, node.serial_io.name))
                        nodes.append(node)
            else:
                logger.error('Unable to fetch revision code for serial node at "{0}"'.format(comm))
    return nodes
