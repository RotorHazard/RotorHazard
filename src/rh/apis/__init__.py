from collections import namedtuple
from rh.interface.BaseHardwareInterface import BaseHardwareInterfaceListener
from typing import Optional


RESET_FREQUENCY = -1

NodeRef = namedtuple('NodeRef', ['timer', 'address', 'index', 'node'])


class RHListener(BaseHardwareInterfaceListener):
    def __init__(self,
                 node_crossing_callback,
                 pass_record_callback,
                 split_record_callback,
                 on_set_frequency,
                 on_set_enter_at_level,
                 on_set_exit_at_level):
        self.node_crossing_callback = node_crossing_callback
        self.pass_record_callback = pass_record_callback
        self.split_record_callback = split_record_callback
        self.on_set_frequency = on_set_frequency
        self.on_set_enter_at_level = on_set_enter_at_level
        self.on_set_exit_at_level = on_set_exit_at_level

    def on_rssi_sample(self, node_ref, ts: int, rssi: int):
        pass

    def on_enter_triggered(self, node_ref, cross_ts: int, cross_rssi: int):
        if node_ref.node:
            self.node_crossing_callback(node_ref.node, True, cross_ts, cross_rssi)

    def on_exit_triggered(self, node_ref, cross_ts: int , cross_rssi: int):
        if node_ref.node:
            self.node_crossing_callback(node_ref.node, False, cross_ts, cross_rssi)

    def on_pass(self, node_ref, lap_ts: int, lap_source, pass_rssi: int):
        if node_ref.node:
            self.pass_record_callback(node_ref.node, lap_ts, lap_source)
        else:
            self.split_record_callback(node_ref.timer, node_ref.address, node_ref.index, lap_ts)

    def on_frequency_changed(self, node_ref, frequency: int, band: Optional[str]=None, channel: Optional[int]=None):
        if node_ref.node:
            if frequency >= 0:
                freq_data = {'node': node_ref.node.index, 'frequency': frequency}
                if frequency > 0 and band is not None and channel is not None:
                    freq_data['band'] = band
                    freq_data['channel'] = channel
                self.on_set_frequency(freq_data)
            elif frequency == RESET_FREQUENCY:
                # clear band/channel assignments
                self.on_set_frequency({'node': node_ref.node.index, 'frequency': node_ref.node.frequency})

    def on_enter_trigger_changed(self, node_ref, level: int):
        if node_ref.node:
            self.on_set_enter_at_level({'node': node_ref.node.index, 'enter_at_level': level})

    def on_exit_trigger_changed(self, node_ref, level: int):
        if node_ref.node:
            self.on_set_exit_at_level({'node': node_ref.node.index, 'exit_at_level': level})
