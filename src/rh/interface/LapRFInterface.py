'''LapRF interface layer.'''

import logging
import gevent
import serial
import socket
from monotonic import monotonic

from .BaseHardwareInterface import BaseHardwareInterface, BaseHardwareInterfaceListener
from .Node import Node, NodeManager
from rh.sensors import Sensor, Reading
from . import laprf_protocol as laprf
from . import ExtremumFilter, ensure_iter
from rh.helpers import serial_url, socket_url

logger = logging.getLogger(__name__)

RESPONSE_WAIT = 0.5  # secs
WRITE_CHILL_TIME = 0.010


class LapRFNodeManager(NodeManager):
    TYPE = "LapRF"

    def __init__(self, addr, io_stream):
        super().__init__()
        self.max_rssi_value = 3500
        self.addr = addr
        self.io_stream = io_stream
        self.stream_buffer = bytearray()
        self.voltage = None
        self.min_lap_time = None
        self.race_start_rtc_time = 0  # usecs
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
        self.history_filter = ExtremumFilter()
        self.pass_count = 0

    def reset(self):
        super().reset()
        self.history_filter = ExtremumFilter()

    @property
    def threshold(self):
        return self._threshold

    @threshold.setter
    def threshold(self, value):
        self._threshold = value
        self.enter_at_level = value
        self.exit_at_level = value


class LapRFInterfaceListener(BaseHardwareInterfaceListener):
    def on_threshold_changed(self, node, threshold):
        pass

    def on_gain_changed(self, node, gain):
        pass


class LapRFInterface(BaseHardwareInterface):
    def __init__(self, addr_streams, listener=None):
        super().__init__(
            listener=listener if listener is not None else LapRFInterfaceListener()
        )
        addr_streams = ensure_iter(addr_streams)
        for addr_stream in addr_streams:
            node_manager = LapRFNodeManager(*addr_stream)
            self.node_manager.append(node_manager)

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
        nm_sleep_interval = self.update_sleep/max(len(self.node_managers), 1)
        if self.node_managers:
            for node_manager in self.node_managers:
                self._poll(node_manager)
                gevent.sleep(nm_sleep_interval)
        else:
            gevent.sleep(nm_sleep_interval)

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
            rssi_ts = monotonic()
            for idx, rssi in enumerate(record.last_rssi):
                if rssi is not None:
                    node = node_manager.nodes[idx]
                    node.current_rssi = rssi
                    node.node_peak_rssi = max(rssi, node.node_peak_rssi)
                    node.node_nadir_rssi = min(rssi, node.node_nadir_rssi)
                    filtered_ts, filtered_rssi = node.history_filter.filter(rssi_ts, rssi)
                    self.append_history(node, filtered_ts, filtered_rssi)
        elif isinstance(record, laprf.PassingEvent):
            node_idx = record.slot_index - 1
            node = node_manager.nodes[node_idx]
            pass_peak_rssi = record.peak_height
            node.node_peak_rssi = max(record.peak_height, node.node_peak_rssi)
            lap_ts = (record.rtc_time - node_manager.race_start_rtc_time)/1000000
            if self.is_racing:
                node.pass_history.append((lap_ts + self.race_start_time, pass_peak_rssi))
            node.pass_count += 1
            self._notify_pass(node, lap_ts, BaseHardwareInterface.LAP_SOURCE_REALTIME, None)
        elif isinstance(record, laprf.RFSetupEvent):
            node_idx = record.slot_index - 1
            node = node_manager.nodes[node_idx]
            node.band_idx = record.band
            node.channel_idx = record.channel
            old_frequency = node.frequency
            old_bandChannel = node.bandChannel
            if record.enabled:
                node.frequency = record.frequency
                if record.band_idx >= 1 and record.band_idx <= len(laprf.LIVE_TIME_BANDS) and record.channel_idx >= 1 and record.channel_idx <= laprf.MAX_CHANNELS:
                    node.bandChannel = laprf.LIVE_TIME_BANDS[record.band_idx-1] + str(record.channel_idx)
                else:
                    node.bandChannel = None
            else:
                node.frequency = 0
                node.bandChannel = None
            old_threshold = node.threshold
            old_gain = node.gain
            node.threshold = record.threshold
            node.gain = record.gain
            node.is_configured = True
            if node.frequency != old_frequency:
                self._notify_frequency_changed(node)
            if node.bandChannel != old_bandChannel:
                self._notify_bandChannel_changed(node)
            if node.threshold != old_threshold:
                self._notify_threshold_changed(node)
            if node.gain != old_gain:
                self._notify_gain_changed(node)
        elif isinstance(record, laprf.TimeEvent):
            if node_manager.race_start_time_request_ts is not None:
                server_oneway = (monotonic() - node_manager.race_start_time_request_ts)/2
                node_manager.race_start_rtc_time = record.rtc_time - server_oneway*1000000  # usecs
                node_manager.race_start_time_request_ts = None
        elif isinstance(record, laprf.SettingsEvent):
            if record.min_lap_time:
                node_manager.min_lap_time = record.min_lap_time
        else:
            logger.warning("Unsupported record: {}".format(record))

    def on_race_start(self, race_start_time):
        super().on_race_start(race_start_time)
        data = laprf.encode_get_rtc_time_record()
        for node_manager in self.node_managers:
            node_manager.race_start_time_request_ts = monotonic()
            node_manager.write(data)

    def set_enter_at_level(self, node_index, level):
        self.set_threshold(node_index, level)

    def set_exit_at_level(self, node_index, level):
        self.set_threshold(node_index, level)

    def set_threshold(self, node_index, threshold):
        if threshold >= 0 and threshold <= laprf.MAX_THRESHOLD:
            node = self.nodes[node_index]
            self.set_rf_setup(node, node.frequency, node.band_idx, node.channel_idx, node.gain, threshold)

    def set_gain(self, node_index, gain):
        if gain >= 0 and gain <= laprf.MAX_GAIN:
            node = self.nodes[node_index]
            self.set_rf_setup(node, node.frequency, node.band_idx, node.channel_idx, gain, node.threshold)

    def set_frequency(self, node_index, frequency, band=None, channel=None):
        node = self.nodes[node_index]
        try:
            band_idx = laprf.LIVE_TIME_BANDS.index(band) + 1 if band else 0
        except ValueError:
            band_idx = 0
        channel_idx = channel if channel else 0
        self.set_rf_setup(node, frequency, band_idx, channel_idx, node.gain, node.threshold)

    def set_rf_setup(self, node, frequency, band_idx, channel_idx, gain, threshold):
        node_manager = node.manager
        slot_index = node.multi_node_index + 1
        enabled = True if frequency else False
        node_manager.write(laprf.encode_set_rf_setup_record(slot_index, enabled, band_idx, channel_idx, frequency if frequency else 0, gain, threshold))
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
        if node.threshold != threshold:
            logger.error("LapRF ignored our request to change the threshold of node {} (requested {}, is {})".format(node, threshold, node.threshold))

    def _notify_threshold_changed(self, node):
        self.listener.on_threshold_changed(node, node.threshold)

    def _notify_gain_changed(self, node):
        self.listener.on_gain_changed(node, node.gain)


class SocketStream:
    def __init__(self, socket):
        self.socket = socket

    def write(self, data):
        self.socket.send(data)

    def read(self, max_size):
        return self.socket.recv(max_size)

    def close(self):
        self.socket.close()


SERIAL_SCHEME = 'serial:'
SOCKET_SCHEME = 'socket://'


def _normalize_addr(addr):
    if not addr.startswith(SERIAL_SCHEME) and not addr.startswith(SOCKET_SCHEME):
        # addr is not a url
        if addr.startswith('/'):
            # assume serial/file
            addr = serial_url(addr)
        else:
            # assume simple <host>[:<port>]
            host_port = addr.split(':')
            if len(host_port) == 1:
                host_port = (host_port[0], 5403)
            addr = socket_url(host_port[0], host_port[1])
    return addr


def _create_stream(addr):
    if addr.startswith(SERIAL_SCHEME):
        port = addr[len(SERIAL_SCHEME):]
        io_stream = serial.Serial(port=port, baudrate=115200, timeout=0.25)
    elif addr.startswith(SOCKET_SCHEME):
        # strip any trailing /
        end_pos = -1 if addr[-1] == '/' else len(addr)
        socket_addr = addr[len(SOCKET_SCHEME):end_pos]
        host_port = socket_addr.split(':')
        if len(host_port) == 1:
            host_port = (host_port[0], 5403)
        io_stream = SocketStream(socket.create_connection(host_port))
    else:
        raise ValueError("Unsupported address: {}".format(addr))
    return io_stream


def get_hardware_interface(config, *args, **kwargs):
    addrs = ensure_iter(config.LAPRF['ADDRESS'])
    addr_streams = []
    for addr in addrs:
        addr  = _normalize_addr(addr)
        io_stream = _create_stream(addr)
        addr_streams.append((addr, io_stream))
    return LapRFInterface(addr_streams)
