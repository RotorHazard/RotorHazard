from collections import namedtuple
from threading import Lock
from rh.interface import RssiSample, LifetimeSample
from rh.interface.BaseHardwareInterface import BaseHardwareInterface, BaseHardwareInterfaceListener
from rh.helpers.mqtt_helper import make_topic
from typing import Optional


RESET_FREQUENCY = -1


class NodeRef(namedtuple('NodeRef', ['timer', 'address', 'index', 'node'])):
    def __hash__(self):
        return hash(self[:3])

    def __eq__(self, other):
        return self[:3] == other[:3]

    def __str__(self):
        return make_topic('', [self.timer, self.address, str(self.index)])


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

    def on_enter_triggered(self, node_ref, cross_ts: int, cross_rssi: int, cross_lifetime: Optional[int]=None):
        if node_ref.node:
            self.node_crossing_callback(node_ref.node, True, cross_ts, cross_rssi)

    def on_exit_triggered(self, node_ref, cross_ts: int , cross_rssi: int, cross_lifetime: Optional[int]=None):
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


class RssiSampleListener(BaseHardwareInterfaceListener):
    MAX_SAMPLES = 20

    def __init__(self):
        self.lock = Lock()
        self.rssi_samples_by_node = {}
        self.lifetime_samples_by_node = {}

    def get_rssis(self):
        with self.lock:
            for samples in self.rssi_samples_by_node.values():
                samples.sort(key=lambda s: s.timestamp)
            return self.rssi_samples_by_node

    def get_lifetimes(self):
        with self.lock:
            for samples in self.lifetime_samples_by_node.values():
                samples.sort(key=lambda s: s.timestamp)
            return self.lifetime_samples_by_node

    def _get_rssi_samples(self, node_ref):
        rssi_samples = self.rssi_samples_by_node.get(node_ref)
        if rssi_samples is None:
            rssi_samples = []
            self.rssi_samples_by_node[node_ref] = rssi_samples
        return rssi_samples

    def _get_lifetime_samples(self, node_ref):
        lifetime_samples = self.lifetime_samples_by_node.get(node_ref)
        if lifetime_samples is None:
            lifetime_samples = []
            self.lifetime_samples_by_node[node_ref] = lifetime_samples
        return lifetime_samples

    def _truncate_samples(self, samples):
        if len(samples) > RssiSampleListener.MAX_SAMPLES:
            samples.sort(key=lambda s: s.timestamp)
            del samples[:-RssiSampleListener.MAX_SAMPLES]

    def on_rssi_sample(self, node_ref, ts: int, rssi: int):
        with self.lock:
            rssi_samples = self._get_rssi_samples(node_ref)
            rssi_samples.append(RssiSample(ts, rssi))
            self._truncate_samples(rssi_samples)

    def on_enter_triggered(self, node_ref, cross_ts: int, cross_rssi: int, cross_lifetime: Optional[int]=None):
        with self.lock:
            rssi_samples = self._get_rssi_samples(node_ref)
            rssi_samples.append(RssiSample(cross_ts, cross_rssi))
            self._truncate_samples(rssi_samples)
            if cross_lifetime is not None:
                lifetime_samples = self._get_lifetime_samples(node_ref)
                lifetime_samples.append(LifetimeSample(cross_ts, cross_lifetime))
                self._truncate_samples(lifetime_samples)

    def on_exit_triggered(self, node_ref, cross_ts: int , cross_rssi: int, cross_lifetime: Optional[int]=None):
        with self.lock:
            rssi_samples = self._get_rssi_samples(node_ref)
            rssi_samples.append(RssiSample(cross_ts, cross_rssi))
            self._truncate_samples(rssi_samples)
            if cross_lifetime is not None:
                lifetime_samples = self._get_lifetime_samples(node_ref)
                # store nadir lifetimes as negatives
                lifetime_samples.append(LifetimeSample(cross_ts, -cross_lifetime))
                self._truncate_samples(lifetime_samples)

    def on_pass(self, node_ref, lap_ts: int, lap_source, pass_rssi: int):
        if lap_source == BaseHardwareInterface.LAP_SOURCE_REALTIME:
            with self.lock:
                rssi_samples = self._get_rssi_samples(node_ref)
                rssi_samples.append(RssiSample(lap_ts, pass_rssi))
                self._truncate_samples(rssi_samples)

    def on_lifetime_sample(self, node_ref, ts: int, lifetime: int):
        with self.lock:
            # lifetimes are negatives for nadirs
            lifetime_samples = self._get_lifetime_samples(node_ref)
            lifetime_samples.append(LifetimeSample(ts, lifetime))
            self._truncate_samples(lifetime_samples)

    def on_extremum_history(self, node_ref, extremum_timestamp: int, extremum_rssi: int, extremum_duration: int):
        with self.lock:
            rssi_samples = self._get_rssi_samples(node_ref)
            rssi_samples.append(RssiSample(extremum_timestamp, extremum_rssi))
            rssi_samples.append(RssiSample(extremum_timestamp + extremum_duration, extremum_rssi))
            self._truncate_samples(rssi_samples)

