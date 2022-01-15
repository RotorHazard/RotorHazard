'''Chorus hardware interface layer.'''

import logging
import gevent
import serial
from monotonic import monotonic

from .BaseHardwareInterface import BaseHardwareInterface
from .Node import Node, NodeManager
from sensors import Sensor, Reading
from interface import ExtremumFilter, ensure_iter
from helpers import serial_url

RETRY_COUNT=5

logger = logging.getLogger(__name__)


class ChorusNodeManager(NodeManager):
    TYPE = "Chorus"

    def __init__(self, serial_io):
        super().__init__()
        self.serial_io = serial_io
        self.max_rssi_value = 2700
        self.addr = serial_url(self.serial_io.port)
        self.voltage = None

    def _create_node(self, index, multi_node_index):
        return ChorusNode(index, multi_node_index, self)

    def write(self, data):
        self.serial_io.write(data.encode('UTF-8'))

    def read(self):
        return self.serial_io.read_until()[:-1]

    def close(self):
        self.serial_io.close()


class ChorusSensor(Sensor):
    def __init__(self, node_manager):
        super().__init__(node_manager.addr, "Chorus")
        self.description = "Chorus"
        self.node_manager = node_manager

    def update(self):
        self.node_manager.write('R*v\n')

    @Reading(units='V')
    def voltage(self):
        return self.node_manager.voltage*55.0/1024.0 if self.node_manager.voltage is not None else None


class ChorusNode(Node):
    def __init__(self, index, multi_node_index, manager):
        super().__init__(index=index, multi_node_index=multi_node_index, manager=manager)
        self.history_filter = ExtremumFilter()

    def reset(self):
        super().reset()
        self.history_filter = ExtremumFilter()

    def send_command(self, command, in_value):
        with self.manager:
            self.manager.write('R{0}{1}{2:04x}\n'.format(self.index, command, in_value))
            out_value = int(self.manager.read()[3:7], 16)
            return out_value

    def set_and_validate_value_4x(self, command, in_value):
        success = False
        retry_count = 0
        out_value = None
        while success is False and retry_count < RETRY_COUNT:
            out_value = self.send_command(command, in_value)
            if out_value == in_value:
                success = True
            else:
                retry_count += 1
                logger.warning('Value Not Set (retry={0}): cmd={1}, val={2}, node={3}'.\
                         format(retry_count, command, in_value, self.index+1))
        return out_value if out_value is not None else in_value


class ChorusInterface(BaseHardwareInterface):
    def __init__(self, serial_ios):
        super().__init__()
        serial_ios = ensure_iter(serial_ios)
        for serial_io in serial_ios:
            node_manager = ChorusNodeManager(serial_io)
            self.node_managers.append(node_manager)

        self.sensors = []

        for node_manager in self.node_managers:
            with node_manager:
                node_manager.write('N0\n')
                resp = node_manager.read()
                if resp:
                    last_node = resp[1]
                else:
                    logger.warning("Invalid response received")

                for index in range(int(last_node)):
                    node = node_manager.add_node(index)
                    self.nodes.append(node)

            self.sensors.append(ChorusSensor(node_manager))

        for node in self.nodes:
            # set minimum lap time to zero - let the server handle it
            node.set_and_validate_value_4x('M', 0)

    #
    # Update Loop
    #

    def _update(self):
        nm_sleep_interval = self.update_sleep/max(len(self.node_managers), 1)
        if self.node_managers:
            for node_manager in self.node_managers:
                with node_manager:
                    data = node_manager.read()
                if data:
                    self._process_message(node_manager, data)
                gevent.sleep(nm_sleep_interval)
        else:
            gevent.sleep(nm_sleep_interval)

    def _process_message(self, node_manager, data):
        if data[0] == 'S':
            multi_node_idx = int(data[1])
            node = node_manager.nodes[multi_node_idx]
            cmd = data[2]
            if cmd == 'L':
                node.pass_count = int(data[3:5], 16)  # lap count
                lap_ts = int(data[5:13], 16)  # relative to start time
                self._notify_pass(node, lap_ts, BaseHardwareInterface.LAP_SOURCE_REALTIME, None)
            elif cmd == 'r':
                rssi = int(data[3:7], 16)
                node.current_rssi = rssi
                node.node_peak_rssi = max(rssi, node.node_peak_rssi)
                node.node_nadir_rssi = min(rssi, node.node_nadir_rssi)
                ts = monotonic()
                filtered_ts, filtered_rssi = node.history_filter.filter(ts, rssi)
                if filtered_rssi is not None:
                    self.append_history(node, filtered_ts, filtered_rssi)
            elif cmd == 'v':
                node.manager.voltage = int(data[3:7], 16)

    def on_race_start(self):
        super().on_race_start()
        # reset timers to zero
        for node_manager in self.node_managers:
            with node_manager:
                # mode = lap times relative to start time
                node_manager.write('R*R2\n')
                node_manager.read()

    def on_race_stop(self):
        for node_manager in self.node_managers:
            with node_manager:
                node_manager.write('R*R0\n')
                node_manager.read()
        super().on_race_stop()

    def transmit_frequency(self, node, frequency):
        return node.set_and_validate_value_4x('F', frequency)

    def transmit_enter_at_level(self, node, level):
        return node.set_and_validate_value_4x('T', level)

    def transmit_exit_at_level(self, node, level):
        return node.set_and_validate_value_4x('T', level)


def get_hardware_interface(config, *args, **kwargs):
    '''Returns the interface object.'''
    ports = ensure_iter(config.CHORUS['HARDWARE_PORT'])
    serial_ios = [serial.Serial(port=port, baudrate=115200, timeout=0.1) for port in ports]
    return ChorusInterface(serial_ios)
