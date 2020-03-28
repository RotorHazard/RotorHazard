'''RotorHazard hardware interface layer.'''

import os
import io
import gevent # For threads and timing
from monotonic import monotonic # to capture read timing

from Node import Node
from BaseHardwareInterface import BaseHardwareInterface, PeakNadirHistory, discover_modules, discover_plugins

READ_ADDRESS = 0x00         # Gets i2c address of arduino (1 byte)
READ_FREQUENCY = 0x03       # Gets channel frequency (2 byte)
READ_LAP_STATS = 0x05
# READ_FILTER_RATIO = 0x20    # node API_level>=10 uses 16-bit value
READ_REVISION_CODE = 0x22   # read NODE_API_LEVEL and verification value
READ_NODE_RSSI_PEAK = 0x23  # read 'nodeRssiPeak' value
READ_NODE_RSSI_NADIR = 0x24  # read 'nodeRssiNadir' value
READ_ENTER_AT_LEVEL = 0x31
READ_EXIT_AT_LEVEL = 0x32
READ_TIME_MILLIS = 0x33     # read current 'millis()' time value

WRITE_FREQUENCY = 0x51      # Sets frequency (2 byte)
# WRITE_FILTER_RATIO = 0x70   # node API_level>=10 uses 16-bit value
WRITE_ENTER_AT_LEVEL = 0x71
WRITE_EXIT_AT_LEVEL = 0x72
FORCE_END_CROSSING = 0x78   # kill current crossing flag regardless of RSSI value

LAPSTATS_FLAG_CROSSING = 0x01  # crossing is in progress
LAPSTATS_FLAG_PEAK = 0x02      # reported extremum is peak

UPDATE_SLEEP = float(os.environ.get('RH_UPDATE_INTERVAL', '0.1')) # Main update loop delay
MAX_RETRY_COUNT = 4 # Limit of I/O retries
MIN_RSSI_VALUE = 1               # reject RSSI readings below this value

def unpack_8(data):
    return data[0]

def pack_8(data):
    return [int(data & 0xFF)]

def unpack_16(data):
    '''Returns the full variable from 2 bytes input.'''
    result = data[0]
    result = (result << 8) | data[1]
    return result

def pack_16(data):
    '''Returns a 2 part array from the full variable.'''
    part_a = (data >> 8)
    part_b = (data & 0xFF)
    return [int(part_a), int(part_b)]

def unpack_32(data):
    '''Returns the full variable from 4 bytes input.'''
    result = data[0]
    result = (result << 8) | data[1]
    result = (result << 8) | data[2]
    result = (result << 8) | data[3]
    return result

def pack_32(data):
    '''Returns a 4 part array from the full variable.'''
    part_a = (data >> 24)
    part_b = (data >> 16) & 0xFF
    part_c = (data >> 8) & 0xFF
    part_d = (data & 0xFF)
    return [int(part_a), int(part_b), int(part_c), int(part_d)]


def calculate_checksum(data):
    checksum = sum(data) & 0xFF
    return checksum

def validate_checksum(data):
    '''Returns True if the checksum matches the data.'''
    if not data:
        return False
    checksum = calculate_checksum(data[:-1])
    return checksum == data[-1]

def unpack_rssi(node, data):
    if node.api_level >= 18:
        return unpack_8(data)
    else:
        return unpack_16(data) / 2


class RHInterface(BaseHardwareInterface):
    def __init__(self, *args, **kwargs):
        BaseHardwareInterface.__init__(self)
        self.update_thread = None # Thread for running the main update loop

        self.intf_read_block_count = 0  # number of blocks read by all nodes
        self.intf_read_error_count = 0  # number of read errors for all nodes
        self.intf_write_block_count = 0  # number of blocks write by all nodes
        self.intf_write_error_count = 0  # number of write errors for all nodes

        extKwargs = {}
        for helper in discover_modules('helper'):
            extKwargs[helper.__name__] = helper.create(self, *args, **kwargs)
        extKwargs.update(kwargs)

        self.nodes = []
        self.discover_nodes(*args, **extKwargs)

        self.data_loggers = []
        for node in self.nodes:
            node.frequency = self.get_value_16(node, READ_FREQUENCY)
            if not node.frequency:
                raise RuntimeError('Unable to read frequency value from node {0}'.format(node.index+1))
                   # read NODE_API_LEVEL and verification value:
            rev_val = self.get_value_16(node, READ_REVISION_CODE)
            if not rev_val:
                raise RuntimeError('Unable to read revision code from node {0}'.format(node.index+1))
            if (rev_val >> 8) == 0x25:  # if verify passed (fn defined) then set API level
                node.api_level = rev_val & 0xFF
            else:
                node.api_level = 0  # if verify failed (fn not defined) then set API level to 0
            node.init()
            if node.api_level >= 10:
                node.node_peak_rssi = self.get_value_rssi(node, READ_NODE_RSSI_PEAK)
                if node.api_level >= 13:
                    node.node_nadir_rssi = self.get_value_rssi(node, READ_NODE_RSSI_NADIR)
                node.enter_at_level = self.get_value_rssi(node, READ_ENTER_AT_LEVEL)
                node.exit_at_level = self.get_value_rssi(node, READ_EXIT_AT_LEVEL)
                print "Node {0}: API_level={1}, Freq={2}, EnterAt={3}, ExitAt={4}".format(node.index+1, node.api_level, node.frequency, node.enter_at_level, node.exit_at_level)

                if "RH_RECORD_NODE_{0}".format(node.index+1) in os.environ:
                    self.data_loggers.append(open("data_{0}.csv".format(node.index+1), 'w'))
                    print("Data logging enabled for node {0}".format(node.index+1))
                else:
                    self.data_loggers.append(None)
            else:
                print("Node {0}: API_level={1}".format(node.index+1, node.api_level))

        sensorKwargs = {}
        sensorKwargs.update(extKwargs)
        del sensorKwargs['config']
        self.discover_sensors(config=kwargs['config'].get('SENSORS', {}), *args, **sensorKwargs)


    def discover_nodes(self, *args, **kwargs):
        self.nodes.extend(discover_plugins('node', *args, **kwargs))


    #
    # Update Loop
    #

    def start(self):
        if self.update_thread is None:
            self.log('Starting background thread')
            self.update_thread = gevent.spawn(self.update_loop)

    def update_loop(self):
        while True:
            try:
                while True:
                    self.update()
                    gevent.sleep(UPDATE_SLEEP)
            except KeyboardInterrupt:
                print("Update thread terminated by keyboard interrupt")
                return
            except Exception as ex:
                self.log('Exception in RHInterface update_loop():  ' + str(ex))
                gevent.sleep(UPDATE_SLEEP*10)

    def update(self):
        upd_list = []  # list of nodes with new laps (node, new_lap_id, lap_timestamp)
        cross_list = []  # list of nodes with crossing-flag changes
        for node in self.nodes:
            if node.frequency:
                if node.api_valid_flag or node.api_level >= 5:
                    if node.api_level >= 21:
                        data = node.read_block(self, READ_LAP_STATS, 16)
                    elif node.api_level >= 18:
                        data = node.read_block(self, READ_LAP_STATS, 19)
                    elif node.api_level >= 17:
                        data = node.read_block(self, READ_LAP_STATS, 28)
                    elif node.api_level >= 13:
                        data = node.read_block(self, READ_LAP_STATS, 20)
                    else:
                        data = node.read_block(self, READ_LAP_STATS, 18)
                    server_roundtrip = node.io_response - node.io_request
                    server_oneway = server_roundtrip / 2
                    readtime = node.io_response - server_oneway
                else:
                    data = node.read_block(self, READ_LAP_STATS, 17)

                if data != None and len(data) > 0:
                    lap_id = data[0]

                    if node.api_level >= 18:
                        offset_rssi = 3
                        offset_nodePeakRssi = 4
                        offset_passPeakRssi = 5
                        offset_loopTime = 6
                        offset_lapStatsFlags = 8
                        offset_passNadirRssi = 9
                        offset_nodeNadirRssi = 10
                        if node.api_level >= 21:
                            offset_peakRssi = 11
                            offset_peakFirstTime = 12
                            offset_peakLastTime = 14
                            offset_nadirRssi = 11
                            offset_nadirFirstTime = 12
                            offset_nadirLastTime = 14
                        else:
                            offset_peakRssi = 11
                            offset_peakFirstTime = 12
                            offset_peakLastTime = 14
                            offset_nadirRssi = 16
                            offset_nadirFirstTime = 17
                    else:
                        offset_rssi = 5
                        offset_nodePeakRssi = 7
                        offset_passPeakRssi = 9
                        offset_loopTime = 11
                        offset_lapStatsFlags = 15
                        offset_passNadirRssi = 16
                        offset_nodeNadirRssi = 18
                        offset_peakRssi = 20
                        offset_peakTime = 22
                        offset_nadirRssi = 24
                        offset_nadirFirstTime = 26

                    rssi_val = unpack_rssi(node, data[offset_rssi:])
                    if node.is_valid_rssi(rssi_val):
                        node.current_rssi = rssi_val

                        cross_flag = None
                        pn_history = None
                        if node.api_valid_flag:  # if newer API functions supported
                            if node.api_level >= 18:
                                ms_val = unpack_16(data[1:])
                                pn_history = PeakNadirHistory(node.index)
                                if node.api_level >= 21:
                                    if data[offset_lapStatsFlags] & LAPSTATS_FLAG_PEAK:
                                        rssi_val = unpack_rssi(node, data[offset_peakRssi:])
                                        if node.is_valid_rssi(rssi_val):
                                            pn_history.peakRssi = rssi_val
                                            pn_history.peakFirstTime = unpack_16(data[offset_peakFirstTime:]) # ms *since* the first peak time
                                            pn_history.peakLastTime = unpack_16(data[offset_peakLastTime:])   # ms *since* the last peak time
                                        elif rssi_val > 0:
                                            self.log('History peak RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node.index+1))
                                    else:
                                        rssi_val = unpack_rssi(node, data[offset_nadirRssi:])
                                        if node.is_valid_rssi(rssi_val):
                                            pn_history.nadirRssi = rssi_val
                                            pn_history.nadirFirstTime = unpack_16(data[offset_nadirFirstTime:])
                                            pn_history.nadirLastTime = unpack_16(data[offset_nadirLastTime:])
                                        elif rssi_val > 0:
                                            self.log('History nadir RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node.index+1))
                                else:
                                    rssi_val = unpack_rssi(node, data[offset_peakRssi:])
                                    if node.is_valid_rssi(rssi_val):
                                        pn_history.peakRssi = rssi_val
                                        pn_history.peakFirstTime = unpack_16(data[offset_peakFirstTime:]) # ms *since* the first peak time
                                        pn_history.peakLastTime = unpack_16(data[offset_peakLastTime:])   # ms *since* the last peak time
                                    rssi_val = unpack_rssi(node, data[offset_nadirRssi:])
                                    if node.is_valid_rssi(rssi_val):
                                        pn_history.nadirRssi = rssi_val
                                        pn_history.nadirFirstTime = unpack_16(data[offset_nadirFirstTime:])
                                        pn_history.nadirLastTime = pn_history.nadirFirstTime
                            else:
                                ms_val = unpack_32(data[1:])

                            rssi_val = unpack_rssi(node, data[offset_nodePeakRssi:])
                            if node.is_valid_rssi(rssi_val):
                                node.node_peak_rssi = rssi_val
                            rssi_val = unpack_rssi(node, data[offset_passPeakRssi:])
                            if node.is_valid_rssi(rssi_val):
                                node.pass_peak_rssi = rssi_val
                            node.loop_time = unpack_16(data[offset_loopTime:])
                            if data[offset_lapStatsFlags] & LAPSTATS_FLAG_CROSSING:
                                cross_flag = True
                            else:
                                cross_flag = False
                            rssi_val = unpack_rssi(node, data[offset_passNadirRssi:])
                            if node.is_valid_rssi(rssi_val):
                                node.pass_nadir_rssi = rssi_val

                            if node.api_level >= 13:
                                rssi_val = unpack_rssi(node, data[offset_nodeNadirRssi:])
                                if node.is_valid_rssi(rssi_val):
                                    node.node_nadir_rssi = rssi_val

                            if node.api_level >= 18:
                                data_logger = self.data_loggers[node.index]
                                if data_logger:
                                    data_logger.write("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15}\n".format(readtime,lap_id, int(ms_val), node.current_rssi, node.node_peak_rssi, node.pass_peak_rssi, node.loop_time, 'T' if cross_flag else 'F', node.pass_nadir_rssi, node.node_nadir_rssi, pn_history.peakRssi, pn_history.peakFirstTime, pn_history.peakLastTime, pn_history.nadirRssi, pn_history.nadirFirstTime, pn_history.nadirLastTime))

                        else:  # if newer API functions not supported
                            ms_val = unpack_32(data[1:])
                            node.pass_peak_rssi = unpack_rssi(node, data[11:])
                            node.loop_time = unpack_32(data[13:])

                        self.process_lap_stats(node, readtime, lap_id, ms_val, cross_flag, pn_history, cross_list, upd_list)

                    else:
                        self.log('RSSI reading ({0}) out of range on Node {1}; rejected'.format(rssi_val, node.index+1))

        # process any nodes with crossing-flag changes
        self.process_crossings(cross_list)

        # process any nodes with new laps detected
        self.process_updates(upd_list)


    #
    # Internal helper functions for setting single values
    #

    def get_value_8(self, node, command):
        data = node.read_block(self, command, 1)
        result = None
        if data != None:
            result = unpack_8(data)
        return result

    def get_value_16(self, node, command):
        data = node.read_block(self, command, 2)
        result = None
        if data != None:
            result = unpack_16(data)
        return result

    def get_value_32(self, node, command):
        data = node.read_block(self, command, 4)
        result = None
        if data != None:
            result = unpack_32(data)
        return result

    def set_and_validate_value_8(self, node, write_command, read_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            node.write_block(self, write_command, pack_8(in_value))
            out_value = self.get_value_8(node, read_command)
            if out_value == in_value:
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0}): {1}/{2}/{3}'.format(retry_count, write_command, in_value, node.index))

        if out_value == None:
            out_value = in_value
        return out_value

    def set_and_validate_value_16(self, node, write_command, read_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            node.write_block(self, write_command, pack_16(in_value))
            out_value = self.get_value_16(node, read_command)
                   # confirm same value (also handle negative value)
            if out_value == in_value or out_value == in_value + (1 << 16):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0}): {1}/{2}/{3}'.format(retry_count, write_command, in_value, node.index))

        if out_value == None:
            out_value = in_value
        return out_value

    def set_and_validate_value_32(self, node, write_command, read_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            node.write_block(self, write_command, pack_32(in_value))
            out_value = self.get_value_32(node, read_command)
                   # confirm same value (also handle negative value)
            if out_value == in_value or out_value == in_value + (1 << 32):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0}): {1}/{2}/{3}'.format(retry_count, write_command, in_value, node.index))

        if out_value == None:
            out_value = in_value
        return out_value

    def set_value_8(self, node, write_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            if node.write_block(self, write_command, pack_8(in_value)):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0}): {1}/{2}/{3}'.format(retry_count, write_command, in_value, node.index))
        return success

    def set_value_32(self, node, write_command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count <= MAX_RETRY_COUNT:
            if node.write_block(self, write_command, pack_32(in_value)):
                success = True
            else:
                retry_count = retry_count + 1
                self.log('Value Not Set ({0}): {1}/{2}/{3}'.format(retry_count, write_command, in_value, node.index))
        return success

    def set_and_validate_value_rssi(self, node, write_command, read_command, in_value):
        if node.api_level >= 18:
            return self.set_and_validate_value_8(node, write_command, read_command, in_value)
        else:
            return self.set_and_validate_value_16(node, write_command, read_command, in_value)

    def get_value_rssi(self, node, command):
        if node.api_level >= 18:
            return self.get_value_8(node, command)
        else:
            return self.get_value_16(node, command)


    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency):
        node = self.nodes[node_index]
        node.debug_pass_count = 0  # reset debug pass count on frequency change
        if frequency:
            node.frequency = self.set_and_validate_value_16(node,
                WRITE_FREQUENCY,
                READ_FREQUENCY,
                frequency)
        else:  # if freq=0 (node disabled) then write default freq, but save 0 value
            self.set_and_validate_value_16(node,
                WRITE_FREQUENCY,
                READ_FREQUENCY,
                5800)
            node.frequency = 0

    def transmit_enter_at_level(self, node, level):
        return self.set_and_validate_value_rssi(node,
            WRITE_ENTER_AT_LEVEL,
            READ_ENTER_AT_LEVEL,
            level)

    def set_enter_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.api_valid_flag and node.is_valid_rssi(level):
            if self.transmit_enter_at_level(node, level):
                node.enter_at_level = level

    def transmit_exit_at_level(self, node, level):
        return self.set_and_validate_value_rssi(node,
            WRITE_EXIT_AT_LEVEL,
            READ_EXIT_AT_LEVEL,
            level)

    def set_exit_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.api_valid_flag and node.is_valid_rssi(level):
            if self.transmit_exit_at_level(node, level):
                node.exit_at_level = level

    def force_end_crossing(self, node_index):
        node = self.nodes[node_index]
        if node.api_level >= 14:
            self.set_value_8(node, FORCE_END_CROSSING, 0)

    def inc_intf_read_block_count(self):
        self.intf_read_block_count += 1

    def inc_intf_read_error_count(self):
        self.intf_read_error_count += 1

    def inc_intf_write_block_count(self):
        self.intf_write_block_count += 1

    def inc_intf_write_error_count(self):
        self.intf_write_error_count += 1

    def get_intf_total_error_count(self):
        return self.intf_read_error_count + self.intf_write_error_count

    def get_intf_error_report_str(self, showWriteFlag=False):
        retStr = "CommErrors:"
        if showWriteFlag or self.intf_write_error_count > 0:
            retStr += "Write:{0}/{1}({2:.2%}),".format(self.intf_write_error_count, self.intf_write_block_count, \
                            (float(self.intf_write_error_count) / float(self.intf_write_block_count)))
        retStr += "Read:{0}/{1}({2:.2%})".format(self.intf_read_error_count, self.intf_read_block_count, \
                            (float(self.intf_read_error_count) / float(self.intf_read_block_count)))
        for node in self.nodes:
            retStr += ", " + node.get_read_error_report_str()
        return retStr

def get_hardware_interface(*args, **kwargs):
    '''Returns the RotorHazard interface object.'''
    return RHInterface(*args, **kwargs)
