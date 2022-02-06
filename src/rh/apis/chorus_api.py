'''Chorus API serial endpoints.'''
import logging
import gevent
from rh.util.RHUtils import FREQS


logger = logging.getLogger(__name__)


class ChorusAPI():
    def __init__(self, serial_io, hwInterface, sensors, on_start, on_stop_race, on_reset_race):
        self.serial_io = serial_io
        self.INTERFACE = hwInterface
        self.SENSORS = sensors
        self.on_start = on_start
        self.on_stop_race = on_stop_race
        self.on_reset_race = on_reset_race
        self.rssi_push_interval_ms = 0
        self.thread = None

    def start(self):
        logger.info('Chorus API started')
        if self.thread is None:
            self.thread = gevent.spawn(self.chorus_api_thread_function)

    def stop(self):
        if self.thread:
            self.thread.kill(block=True, timeout=0.5)
            self.thread = None
        logger.info('Chorus API stopped')

    def emit_pass_record(self, node, lap_number: int, lap_time_stamp: int):
        self.serial_io.write("S{0}L{1:02x}{2:08x}\n".format(node.index, lap_number, lap_time_stamp).encode("UTF-8"))

    def emit_rssi(self, node_addr):
        self.serial_io.write(self._getRssiResponse(node_addr).encode("UTF-8"))

    def _getRssiResponse(self, node_addr):
        node_data = self.INTERFACE.get_heartbeat_json()
        response = ''
        for i, rssi in enumerate(node_data['current_rssi']):
            if node_addr == '*' or int(node_addr) == i:
                response += 'S{0}r{1:04x}\n'.format(i, rssi)
        return response

    def _getVoltageResponse(self):
        for sensor in self.SENSORS:
            for sensorReading in sensor.getReadings().values():
                if sensorReading['units'] == 'V':
                    return 'S{0}v{1:04x}\n'.format(0, int(sensorReading['value']*1024.0/55.0))
        return ''

    def _process_message(self, data):
        num_nodes = len(self.INTERFACE.nodes)
        response = None
        if data:
            if data == 'N0':
                self.on_start()
                response = 'N{0}\n'.format(num_nodes)
            elif data[0] == 'R' and len(data) >= 3:
                node_addr = data[1]
                cmd = data[2]
                is_setter = len(data) > 3
                if cmd == 'r':
                    response = self._getRssiResponse(node_addr)
                elif cmd == 't':
                    response = ''
                    for i in range(num_nodes):
                        if node_addr == '*' or int(node_addr) == i:
                            response += 'S{0}t{1:04x}\n'.format(i, 0)
                elif cmd == 'v':
                    response = self._getVoltageResponse()
                elif cmd == 'y':
                    response = ''
                    for i in range(num_nodes):
                        response += 'S{0}y0\n'.format(i)
                elif cmd == '#':
                    response = ''
                    for i in range(num_nodes):
                        response += 'S{0}#0004\n'.format(i)
                elif cmd == 'B':
                    node_index = int(node_addr)
                    bandChannel = self.INTERFACE.nodes[node_index].bandChannel
                    if is_setter:
                        band = data[3]
                        chan = int(bandChannel[1]) if bandChannel is not None else 0
                        freq = self.INTERFACE.nodes[node_index].frequency
                        if chan > 0:
                            bandChannel = band + str(chan)
                            if bandChannel in FREQS:
                                freq = FREQS[bandChannel]
                                self.INTERFACE.set_frequency(node_index, freq, band, chan)
                        response = 'S{0}B{1}\nS{0}F{2:04x}\n'.format(node_index, band, freq)
                    else:
                        band = bandChannel[0] if bandChannel is not None else 0
                        response = 'S{0}B{1}'.format(node_index, band)
                elif cmd == 'C':
                    node_index = int(node_addr)
                    bandChannel = self.INTERFACE.nodes[node_index].bandChannel
                    if is_setter:
                        band = bandChannel[0] if bandChannel is not None else ''
                        chan = data[3]
                        freq = self.INTERFACE.nodes[node_index].frequency
                        if band:
                            bandChannel = band + str(chan)
                            if bandChannel in FREQS:
                                freq = FREQS[bandChannel]
                                self.INTERFACE.set_frequency(node_index, freq, band, chan)
                        response = 'S{0}C{1}\nS{0}F{2:04x}\n'.format(node_index, chan, freq)
                    else:
                        chan = int(bandChannel[1]) if bandChannel is not None else 0
                        response = 'S{0}C{1}'.format(node_index, chan)
                elif cmd == 'F':
                    node_index = int(node_addr)
                    if is_setter:
                        freq = int(data[3:7], 16)
                        self.INTERFACE.set_frequency(node_index, freq)
                    else:
                        freq = self.INTERFACE.nodes[node_index].frequency
                    response = 'S{0}F{1:04x}\n'.format(node_index, freq)
                elif cmd == 'I':
                    if is_setter:
                        self.rssi_push_interval_ms = int(data[3:7], 16)
                        response = ''
                        for i in range(num_nodes):
                            response += 'S{0}I{1:04x}\n'.format(i, int(self.rssi_push_interval_ms))
                elif cmd == '1':
                    node_index = int(node_addr)
                    if is_setter:
                        flag = data[3]
                        response = 'S{0}1{1}\n'.format(node_index, flag)
                elif cmd == 'J':
                    node_index = int(node_addr)
                    time_adjust = int(data[3:11], 16)
                    response = 'S{0}J{1:08x}\n'.format(node_index, time_adjust)
                elif cmd == 'M':
                    node_index = int(node_addr)
                    min_lap_time = int(data[3:5], 16)
                    response = 'S{0}M{1:02x}\n'.format(node_index, min_lap_time)
                elif cmd == 'S':
                    if is_setter:
                        flag = data[3]
                        response = ''
                        for i in range(num_nodes):
                            if node_addr == '*' or int(node_addr) == i:
                                response += 'S{0}S{1}\n'.format(i, flag)
                elif cmd == 'T':
                    node_index = int(node_addr)
                    level = int(data[3:7], 16)
                    self.INTERFACE.set_enter_at_level(node_index, level)
                    self.INTERFACE.set_exit_at_level(node_index, level)
                    response = 'S{0}T{1:04x}\n'.format(node_index, level)
                elif cmd == 'R':
                    if data[3] == '0':
                        self.on_stop_race()
                        response = ''
                        for i in range(num_nodes):
                            response += 'S{0}R0\n'.format(i)
                    elif data[3] == '2':
                        self.on_reset_race()
                        response = ''
                        for i in range(num_nodes):
                            response += 'S{0}R2\n'.format(i)
        elif self.rssi_push_interval_ms > 0:
            gevent.sleep(self.rssi_push_interval_ms)
            response = self._getRssiResponse('*')
        else:
            gevent.sleep(0.1)
        return response

    def chorus_api_thread_function(self):
        while True:
            data = self.serial_io.read_until()[:-1]
            response = self._process_message(data)
            if response:
                self.serial_io.write(response.encode('UTF-8'))
            elif data and response is None:
                logger.info('Not yet supported: {0}', data)
