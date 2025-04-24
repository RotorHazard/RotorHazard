'''Interface mapping abstraction'''

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class InterfaceType:
    MOCK = 0
    RH = 1
    RHAPI = 2

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
        self._interface_map = []
        self._node_map = []

    def add_interface(self, interface, if_type:InterfaceType, args=None):
        self._interface_map.append(InterfaceMeta(interface, if_type))

        for node in interface.nodes:  # store node provider and type
            node.provider = interface
            node.provider_type = if_type

        if if_type == InterfaceType.MOCK:
            for node in interface.nodes:  # put mock nodes at latest API level
                node.api_level = args['api_level']

        for idx, node in enumerate(interface.nodes):
            self._node_map.append(
                NodeMap(
                    interface=interface,
                    type=if_type,
                    index=idx,
                    object=node
                )
            )

    def add_callbacks(self):
        for ifmeta in self._interface_map:
            ifmeta.interface.pass_record_callback = self.pass_record_callback
            ifmeta.interface.new_enter_or_exit_at_callback = self.new_enter_or_exit_at_callback
            ifmeta.interface.node_crossing_callback = self.node_crossing_callback

    def reindex_nodes(self):
        for idx, node_map in enumerate(self._node_map):
            node_map.object.index = idx

    @property
    def mapped_interfaces(self):
        return self._interface_map

    @property
    def nodes(self):
        nodelist = []
        for node in self._node_map:
            nodelist.append(node.object)
        return nodelist

    def pass_record_callback(self):
        pass

    def new_enter_or_exit_at_callback(self):
        pass

    def node_crossing_callback(self):
        pass

    def start(self):
        for iface in self._interface_map:
            iface.interface.start()

    def stop(self):
        for iface in self._interface_map:
            iface.interface.stop()

    def update_loop(self):
        for iface in self._interface_map:
            iface.interface.update_loop()

    def update(self):
        for iface in self._interface_map:
            iface.interface.update()

    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency, band, channel):
        mapped_node = self._node_map[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.set_frequency(local_index, frequency, band, channel)

    def transmit_enter_at_level(self, node, level):
        for mapped_node in self._node_map:
            if node == mapped_node:
                return mapped_node.interface.transmit_enter_at_level(node, level)

    def set_enter_at_level(self, node_index, level):
        mapped_node = self._node_map[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.set_enter_at_level(local_index, level)

    def transmit_exit_at_level(self, node, level):
        for mapped_node in self._node_map:
            if node == mapped_node:
                return mapped_node.interface.transmit_exit_at_level(node, level)

    def set_exit_at_level(self, node_index, level):
        mapped_node = self._node_map[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.set_exit_at_level(local_index, level)

    def force_end_crossing(self, node_index):
        mapped_node = self._node_map[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.force_end_crossing(local_index)

    def jump_to_bootloader(self):
        for iface in self._interface_map:
            iface.interface.jump_to_bootloader()

    def send_status_message(self, msgTypeVal, msgDataVal):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.send_status_message()

    def send_shutdown_button_state(self, stateVal):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.send_shutdown_button_state()

    def send_shutdown_started_message(self):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.send_shutdown_started_message()

    def send_server_idle_message(self):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.send_server_idle_message()

    def get_fwupd_serial_name(self):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.get_fwupd_serial_name()

    def close_fwupd_serial_port(self):
        for iface in self._interface_map:
            iface.interface.close_fwupd_serial_port()

    def get_info_node_obj(self):
        return self.nodes[0] if self.nodes and len(self.nodes) > 0 else None

    def get_intf_total_error_count(self):
        count = 0
        for iface in self._interface_map:
            count += iface.interface.get_intf_total_error_count()
        return count

    def set_intf_error_report_percent_limit(self, percentVal):
        for iface in self._interface_map:
            iface.interface.set_intf_error_report_percent_limit(percentVal)

    def get_intf_error_report_str(self, **kwargs):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.get_intf_error_report_str(**kwargs)

    # From Base

    def get_lap_source_str(self, source_idx):
        return self._interface_map[0].interface.get_lap_source_str(source_idx)

    #
    # External functions for setting data
    #

    def intf_simulate_lap(self, node_index, ms_val):
        mapped_node = self._node_map[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.intf_simulate_lap(local_index, ms_val)

    def set_race_status(self, race_status):
        for iface in self._interface_map:
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
        mapped_node = self._node_map[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.start_capture_enter_at_level(local_index)

    def start_capture_exit_at_level(self, node_index):
        mapped_node = self._node_map[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.start_capture_exit_at_level(local_index)

    #
    # Get Json Node Data Functions
    #

    def get_heartbeat_json(self):
        json = {}
        for iface in self._interface_map:
            data = iface.interface.get_heartbeat_json()
            for key, val in data.items():
                if key in json:
                    json[key].extend(data[key])
                else:
                    json[key] = val
        return json
