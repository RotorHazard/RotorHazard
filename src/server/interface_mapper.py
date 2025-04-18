'''Interface mapping abstraction'''

import logging
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class InterfaceType:
    MOCK = 0
    RH = 1

@dataclass
class NodeMap:
    interface: any
    type: InterfaceType
    index: int
    object: any

@dataclass
class InterfaceMeta:
    interface: any
    type: InterfaceType


class InterfaceMapper:
    def __init__(self):
        self._interfaces = []
        self._nodemap = []

    def add_interface(self, interface, if_type:InterfaceType):
        interface.pass_record_callback = self.pass_record_callback
        interface.new_enter_or_exit_at_callback = self.new_enter_or_exit_at_callback
        interface.node_crossing_callback = self.node_crossing_callback
        self._interfaces.append(InterfaceMeta(interface, if_type))
        for idx, node in enumerate(interface.nodes):
            self._nodemap.append(
                NodeMap(
                    interface=interface,
                    type=if_type,
                    index=idx,
                    object=node
                )
            )

    @property
    def nodes(self):
        nodelist = []
        for node in self._nodemap:
            nodelist.append(node.object)
        return nodelist

    def pass_record_callback(self):
        pass

    def new_enter_or_exit_at_callback(self):
        pass

    def node_crossing_callback(self):
        pass

    def start(self):
        for iface in self._interfaces:
            iface.interface.start()

    def stop(self):
        for iface in self._interfaces:
            iface.interface.stop()

    def update_loop(self):
        for iface in self._interfaces:
            iface.interface.update_loop()

    def update(self):
        for iface in self._interfaces:
            iface.interface.update()

    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency):
        mapped_node = self._nodemap[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.set_frequency(local_index, frequency)

    def transmit_enter_at_level(self, node, level):
        for mapped_node in self._nodemap:
            if node == mapped_node:
                return mapped_node.interface.transmit_enter_at_level(node, level)

    def set_enter_at_level(self, node_index, level):
        mapped_node = self._nodemap[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.set_enter_at_level(local_index, level)

    def transmit_exit_at_level(self, node, level):
        for mapped_node in self._nodemap:
            if node == mapped_node:
                return mapped_node.interface.transmit_exit_at_level(node, level)

    def set_exit_at_level(self, node_index, level):
        mapped_node = self._nodemap[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.set_exit_at_level(local_index, level)

    def force_end_crossing(self, node_index):
        mapped_node = self._nodemap[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.force_end_crossing(local_index)

    def jump_to_bootloader(self):
        for iface in self._interfaces:
            iface.interface.jump_to_bootloader()

    def send_status_message(self, msgTypeVal, msgDataVal):
        for iface in self._interfaces:
            iface.interface.send_status_message()
        return False # TODO: Return value

    def send_shutdown_button_state(self, stateVal):
        for iface in self._interfaces:
            iface.interface.send_shutdown_button_state()
        return False # TODO: Return value

    def send_shutdown_started_message(self):
        for iface in self._interfaces:
            iface.interface.send_shutdown_started_message()
        return False # TODO: Return value

    def send_server_idle_message(self):
        for iface in self._interfaces:
            iface.interface.send_server_idle_message()
        return False # TODO: Return value

    def get_fwupd_serial_name(self):
        for iface in self._interfaces:
            iface.interface.get_fwupd_serial_name()
        return None # TODO: Return value

    def close_fwupd_serial_port(self):
        for iface in self._interfaces:
            iface.interface.close_fwupd_serial_port()

    def get_info_node_obj(self):
        return self.nodes[0] if self.nodes and len(self.nodes) > 0 else None

    def get_intf_total_error_count(self):
        count = 0
        for iface in self._interfaces:
            count += iface.interface.get_intf_total_error_count()
        return count

    def set_intf_error_report_percent_limit(self, percentVal):
        for iface in self._interfaces:
            iface.interface.set_intf_error_report_percent_limit(percentVal)

    def get_intf_error_report_str(self, **kwargs):
        for iface in self._interfaces:
            iface.interface.get_intf_error_report_str(**kwargs)
        return None # TODO: Return value




    def get_lap_source_str(self, source_idx):
        return self._interfaces[0].get_lap_source_str(source_idx)

    #
    # External functions for setting data
    #

    def intf_simulate_lap(self, node_index, ms_val):
        mapped_node = self._nodemap[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.intf_simulate_lap(local_index, ms_val)

    def set_race_status(self, race_status):
        for iface in self._interfaces:
            iface.interface.set_race_status(race_status)

    def set_calibration_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def enable_calibration_mode(self):
        pass  # dummy function; no longer supported

    def set_calibration_offset_global(self, offset):
        return offset  # dummy function; no longer supported

    def set_trigger_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def start_capture_enter_at_level(self, node_index):
        mapped_node = self._nodemap[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.start_capture_enter_at_level(local_index)

    def start_capture_exit_at_level(self, node_index):
        mapped_node = self._nodemap[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.start_capture_exit_at_level(local_index)

    #
    # Get Json Node Data Functions
    #

    def get_heartbeat_json(self):
        json = {}
        for iface in self._interfaces:
            data = iface.interface.get_heartbeat_json()
            for key, val in data.items():
                if key in json:
                    json[key].extend(data[key])
                else:
                    json[key] = val
        return json

    def set_frequency(self, node_index, frequency):
        mapped_node = self._nodemap[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.set_frequency(local_index, frequency)
