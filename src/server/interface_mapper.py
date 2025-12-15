'''Interface mapping abstraction'''

import logging
from dataclasses import dataclass
from eventmanager import Evt

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
    def __init__(self, racecontext):
        self._interface_map = []
        self._node_map = []
        self._racecontext = racecontext

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

    def get_rh_interface(self):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface
        return None

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

    def set_all_frequencies(self, freqs):
        '''do hardware update for frequencies'''
        logger.debug("Sending frequency values to all nodes: " + str(freqs["f"]))
        for idx, node in enumerate(self.nodes):
            self.set_frequency(idx, freqs["f"][idx], freqs["b"][idx], freqs["c"][idx])

            self._racecontext.events.trigger(Evt.FREQUENCY_SET, {
                'nodeIndex': idx,
                'frequency': freqs["f"][idx],
                'band': freqs["b"][idx],
                'channel': freqs["c"][idx]
            })

    def set_frequency(self, node_index, frequency, band, channel):
        mapped_node = self._node_map[node_index]
        local_index = mapped_node.index
        result = mapped_node.interface.set_frequency(local_index, frequency, band, channel)
        if result is False:
            logger.warning("Node {} failed register test; check RX SPI communications".format(node_index + 1))
            if mapped_node.object.current_rssi:
                self._racecontext.rhui.emit_priority_message(
                    self._racecontext.language.__('Failed to set frequency on node {}').format(node_index + 1)
                )
            if not self._racecontext.rhui.is_ui_message_set("rx-register-fail-{}".format(node_index)):
                self._racecontext.rhui.set_ui_message("rx-register-fail-{}".format(node_index),\
                           f'{self._racecontext.language.__("Failed to set frequency on node {}.").format(node_index + 1)} (<a href=\"/docs?d=Hardware Setup.md#rx5808-video-receivers\">{self._racecontext.language.__("Check that SPI is enabled for this receiver.")}</a>)',\
                           header="Warning", subclass="errors-logged")

    def transmit_enter_at_level(self, node, level):
        for mapped_node in self._node_map:
            if node == mapped_node:
                return mapped_node.interface.transmit_enter_at_level(node, level)
        return None

    def set_enter_at_level(self, node_index, level):
        mapped_node = self._node_map[node_index]
        local_index = mapped_node.index
        return mapped_node.interface.set_enter_at_level(local_index, level)

    def transmit_exit_at_level(self, node, level):
        for mapped_node in self._node_map:
            if node == mapped_node:
                return mapped_node.interface.transmit_exit_at_level(node, level)
        return None

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
                return iface.interface.send_status_message(msgTypeVal, msgDataVal)
        return None

    def send_shutdown_button_state(self, stateVal):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.send_shutdown_button_state(stateVal)
        return None

    def send_shutdown_started_message(self):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.send_shutdown_started_message()
        return None

    def send_server_idle_message(self):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.send_server_idle_message()
        return None

    def set_fwupd_serial_obj(self, serial_obj):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.set_fwupd_serial_obj(serial_obj)
        return None

    def set_mock_fwupd_serial_obj(self, port_name):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.set_mock_fwupd_serial_obj(port_name)
        return None

    def get_fwupd_serial_name(self):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.get_fwupd_serial_name()
        return None

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

    def get_intf_error_report_str(self, *args, **kwargs):
        for iface in self._interface_map:
            if iface.type == InterfaceType.RH:
                return iface.interface.get_intf_error_report_str(*args, **kwargs)
        return None

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
