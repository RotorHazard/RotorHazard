import logging
import gevent
import serial
import socket
from monotonic import monotonic

from .BaseHardwareInterface import BaseHardwareInterface
from .Node import Node, NodeManager
from sensors import Sensor, Reading
import interface.laprf_protocol as laprf

logger = logging.getLogger(__name__)

RESPONSE_WAIT = 0.5 # secs
WRITE_CHILL_TIME = 0.010

class LapRFNodeManager(NodeManager):
    def __init__(self, addr, io_stream):
        super().__init__()
        self.api_valid_flag = True
        self.max_rssi_value = 3500
        self.addr = addr
        self.io_stream = io_stream
        self.stream_buffer = bytearray()
        self.voltage = None
        self.min_lap_time = None
        self.race_start_rtc_time = None # usecs
        self.race_start_time_request_ts = None
        self.last_write_ts = 0

    def _create_node(self, index, multi_node_index):
        return LapRFNode(index, multi_node_index, self)

    def is_configured(self):
        for node in self.nodes:
            if not node.is_configured:
                return False
        return True

    def write(self, data):
        chill_remaining = self.last_write_ts + WRITE_CHILL_TIME - monotonic()
        if chill_remaining > 0:
            gevent.sleep(chill_remaining)
        self.io_stream.write(data)
        self.last_write_ts = monotonic()

    def read(self):
        return self.io_stream.read(512)

    def close(self):
        self.io_stream.close()


class LapRFSensor(Sensor):
    def __init__(self, node_manager):
        super().__init__(node_manager.addr, "LapRF")
        self.description = "LapRF"
        self.node_manager = node_manager

    @Reading(units='V')
    def voltage(self):
        return self.node_manager.voltage if self.node_manager.voltage is not None else None


class LapRFNode(Node):
    def __init__(self, index, multi_node_index, manager):
        super().__init__(index=index, multi_node_index=multi_node_index, manager=manager)
        self.is_configured = False


class LapRFInterface(BaseHardwareInterface):
    def __init__(self, addr, io_stream):
        super().__init__()
        node_manager = LapRFNodeManager(addr, io_stream)
        self.node_managers = [node_manager]
        self.sensors = []

        for node_manager in self.node_managers:
            with node_manager:
                for index in range(laprf.MAX_SLOTS):
                    node = node_manager.add_node(index)
                    self.nodes.append(node)
            node_manager.write(laprf.encode_set_min_lap_time_record(1))
            node_manager.write(laprf.encode_get_rf_setup_record())
            config_start_ts = monotonic()
            while not node_manager.is_configured() and monotonic() < config_start_ts + RESPONSE_WAIT:
                self._poll(node_manager)
            if not node_manager.is_configured():
                raise Exception("LapRF did not respond with RF setup information")
            self.sensors.append(LapRFSensor(node_manager))

    def _update(self):
        for node_manager in self.node_managers:
            self._poll(node_manager)

    def _poll(self, node_manager):
        with node_manager:
            data = node_manager.read()
        if data:
            end = data.rfind(laprf.EOR)
            if end == -1:
                node_manager.stream_buffer.extend(data)
                return

            records = laprf.decode(node_manager.stream_buffer + data[:end+1])
            node_manager.stream_buffer = bytearray(data[end+1:])
            for record in records:
                self._process_message(node_manager, record)

    def _process_message(self, node_manager, record):
        if isinstance(record, laprf.StatusEvent):
            node_manager.voltage = record.battery_voltage/1000
            for idx, rssi in enumerate(record.last_rssi):
                if rssi is not None:
                    node = node_manager.nodes[idx]
                    node.current_rssi = rssi
                    node.node_peak_rssi = max(rssi, node.node_peak_rssi)
                    node.node_nadir_rssi = min(rssi, node.node_nadir_rssi)
        elif isinstance(record, laprf.PassingEvent):
            node_idx = record.slot_index - 1
            node = node_manager.nodes[node_idx]
            node.pass_peak_rssi = record.peak_height
            node.node_peak_rssi = max(record.peak_height, node.node_peak_rssi)
            start_time_secs = node_manager.race_start_rtc_time/1000000 if node_manager.race_start_rtc_time is not None else 0
            pass_time_secs = record.rtc_time/1000000
            gevent.spawn(self.pass_record_callback, node, pass_time_secs, BaseHardwareInterface.LAP_SOURCE_REALTIME, start_time_secs)
        elif isinstance(record, laprf.RFSetupEvent):
            node_idx = record.slot_index - 1
            node = node_manager.nodes[node_idx]
            node.band = record.band
            node.channel = record.channel
            node.frequency = record.frequency if record.enabled else 0
            node.threshold = record.threshold
            node.gain = record.gain
            node.is_configured = True
        elif isinstance(record, laprf.TimeEvent):
            if node_manager.race_start_time_request_ts is not None:
                server_oneway = (monotonic() - node_manager.race_start_time_request_ts)/2
                node_manager.race_start_rtc_time = record.rtc_time - server_oneway*1000000 # usecs
                node_manager.race_start_time_request_ts = None
        elif isinstance(record, laprf.SettingsEvent):
            if record.min_lap_time:
                node_manager.min_lap_time = record.min_lap_time
        else:
            logger.warning("Unsupported record: {}".format(record))

    def set_race_status(self, race_status):
        if race_status == BaseHardwareInterface.RACE_STATUS_RACING:
            data = laprf.encode_get_rtc_time_record()
            for node_manager in self.node_managers:
                node_manager.race_start_time_request_ts = monotonic()
                node_manager.write(data)
        elif race_status == BaseHardwareInterface.RACE_STATUS_DONE:
            for node_manager in self.node_managers:
                node_manager.race_start_rtc_time = None
        super().set_race_status(race_status)

    def set_enter_at_level(self, node_index, level):
        pass

    def set_exit_at_level(self, node_index, level):
        pass

    def set_frequency(self, node_index, frequency, band='', channel=0):
        node = self.nodes[node_index]
        node_manager = node.manager
        slot_index = node.multi_node_index + 1
        enabled = True if frequency else False
        try:
            band_idx = laprf.LIVE_TIME_BANDS.index(band) + 1
        except ValueError:
            band_idx = 0
        channel_idx = channel if channel else 0
        node_manager.write(laprf.encode_set_rf_setup_record(slot_index, enabled, band_idx, channel_idx, frequency if frequency else 0, node.gain, node.threshold))
        node.is_configured = False
        node_manager.write(laprf.encode_get_rf_setup_record(slot_index))
        config_start_ts = monotonic()
        while not node.is_configured and monotonic() < config_start_ts + RESPONSE_WAIT:
            if self.update_thread:
                gevent.sleep(RESPONSE_WAIT)
            else:
                self._poll(node_manager)
        if not node.is_configured:
            logger.error("LapRF did not respond with RF setup information for node {}".format(node))
        if node.frequency != frequency:
            logger.error("LapRF ignored our request to change the frequency of node {} (requested {}, is {})".format(node, frequency, node.frequency))


class SocketStream:
    def __init__(self, socket):
        self.socket = socket

    def write(self, data):
        self.socket.send(data)

    def read(self, max_size):
        return self.socket.recv(max_size)

    def close(self):
        self.socket.close()


def get_hardware_interface(*args, **kwargs):
    SERIAL_SCHEME = 'serial:'
    addr = kwargs['config'].LAPRF['ADDRESS']
    if addr.startswith(SERIAL_SCHEME):
        port = addr[len(SERIAL_SCHEME)]
        io_stream = serial.Serial(port=port, baudrate=115200, timeout=0.25)
    else:
        host_port = addr.split(':')
        if len(host_port) == 1:
            host_port = (host_port[0], 5403)
        addr = "socket://{}:{}/".format(host_port[0], host_port[1])
        io_stream = SocketStream(socket.create_connection(host_port))
    return LapRFInterface(addr, io_stream)
