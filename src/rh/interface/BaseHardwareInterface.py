import os
import gevent
import inspect
import logging
from collections import UserList
import rh.util.persistent_homology as ph
from rh.util.RHUtils import FREQUENCY_ID_NONE
from rh.util import ms_counter
from .Node import DataStatus, Node, NodeManager
from rh.sensors import Sensor
from . import RssiSample, LifetimeSample
import bisect
from typing import Any, Dict, List, Tuple, Optional


ENTER_AT_PEAK_MARGIN = 5  # closest that captured enter-at level can be to node peak RSSI
CAP_ENTER_EXIT_AT_MS = 3000  # number of milliseconds for capture of enter/exit-at levels

logger = logging.getLogger(__name__)


class BaseHardwareInterfaceListener:
    def on_rssi_sample(self, node, ts: int, rssi: int):
        pass

    def on_lifetime_sample(self, node, ts: int, lifetime: int):
        pass

    def on_enter_triggered(self, node, cross_ts: int, cross_rssi: int, cross_lifetime: Optional[int]=None):
        pass

    def on_exit_triggered(self, node, cross_ts: int , cross_rssi: int, cross_lifetime: Optional[int]=None):
        pass

    def on_pass(self, node, lap_ts: int, lap_source, pass_rssi: int):
        pass

    def on_extremum_history(self, node, extremum_timestamp: int, extremum_rssi: int, extremum_duration: int):
        pass

    def on_frequency_changed(self, node, frequency: int, band: Optional[str]=None, channel: Optional[int]=None):
        pass

    def on_enter_trigger_changed(self, node, level: int):
        pass

    def on_exit_trigger_changed(self, node, level: int):
        pass


class BaseHardwareInterfaceEventBroadcaster(UserList,BaseHardwareInterfaceListener):
    pass


def _broadcast_wrap(attr):
    def _broadcast(self: BaseHardwareInterfaceEventBroadcaster, *args):
        for l in self.data:
            getattr(l, attr)(*args)
    return _broadcast


for attr, value in inspect.getmembers(BaseHardwareInterfaceListener, callable):
    if attr.startswith('on_'):
        setattr(BaseHardwareInterfaceEventBroadcaster, attr, _broadcast_wrap(attr))


class BaseHardwareInterface:

    LAP_SOURCE_REALTIME = 0
    LAP_SOURCE_MANUAL = 1
    LAP_SOURCE_RECALC = 2

    RACE_STATUS_READY = 0
    RACE_STATUS_RACING = 1
    RACE_STATUS_DONE = 2

    def __init__(self, listener=None, update_sleep=0.1):
        self.node_managers: List[NodeManager] = []
        self.nodes: List[Node] = []
        self.sensors: List[Sensor] = []
        # Main update loop delay
        self.update_sleep = float(os.environ.get('RH_UPDATE_INTERVAL', update_sleep))
        self.update_thread = None  # Thread for running the main update loop
        self.environmental_data_update_tracker = 0
        self.race_start_time_ms: int = 0
        self.is_racing = False
        self.listener = listener if listener is not None else BaseHardwareInterfaceListener()
        self.pass_count_mask = 0xFF
        self.intf_error_report_limit = 0.0  # log if ratio of comm errors is larger

    def start(self):
        if self.update_thread is None:
            logger.info('Starting {} background thread'.format(type(self).__name__))
            self.update_thread = gevent.spawn(self._update_loop)

    def stop(self):
        if self.update_thread:
            logger.info('Stopping {} background thread'.format(type(self).__name__))
            self.update_thread.kill(block=True, timeout=0.5)
            self.update_thread = None

    def close(self):
        for node in self.nodes:
            node.summary_stats()
        for manager in self.node_managers:
            manager.close()

    def _notify_rssi_sample(self, node, ts: int, rssi: int):
        self.listener.on_rssi_sample(node, ts, rssi)

    def _notify_lifetime_sample(self, node, ts: int, lifetime: int):
        self.listener.on_lifetime_sample(node, ts, lifetime)

    def _notify_enter_triggered(self, node, trigger_ts: int, trigger_rssi: int, trigger_lifetime: int):
        self.listener.on_enter_triggered(node, trigger_ts, trigger_rssi, trigger_lifetime)

    def _notify_exit_triggered(self, node, trigger_ts: int, trigger_rssi: int, trigger_lifetime: int):
        self.listener.on_exit_triggered(node, trigger_ts, trigger_rssi, trigger_lifetime)

    def _notify_pass(self, node, lap_ts_ms: int, lap_source, pass_rssi: int):
        self.listener.on_pass(node, lap_ts_ms, lap_source, pass_rssi)

    def _notify_extremum_history(self, node, extremum_timestamp, extremum_rssi, extremum_duration):
        self.append_history(node, extremum_timestamp, extremum_rssi, extremum_duration)
        self.listener.on_extremum_history(node, extremum_timestamp, extremum_rssi, extremum_duration)

    def _notify_frequency_changed(self, node):
        if node.bandChannel:
            self.listener.on_frequency_changed(node, node.frequency, band=node.bandChannel[0], channel=int(node.bandChannel[1]))
        else:
            self.listener.on_frequency_changed(node, node.frequency)

    def _notify_enter_trigger_changed(self, node):
        self.listener.on_enter_trigger_changed(node, node.enter_at_level)

    def _notify_exit_trigger_changed(self, node):
        self.listener.on_exit_trigger_changed(node, node.exit_at_level)

    def _update_loop(self):
        while True:
            try:
                self._update()
            except KeyboardInterrupt:
                logger.info("Update thread terminated by keyboard interrupt")
                raise
            except OSError:
                raise
            except SystemExit:
                raise
            except Exception:
                logger.exception('Exception in {} _update_loop():'.format(type(self).__name__))

    def lap_count_change(self, new_count, old_count):
        delta = new_count - old_count
        # handle unsigned roll-over
        if self.pass_count_mask is not None:
            delta = delta & self.pass_count_mask
        return delta

    def is_new_lap(self, node, timestamp: int, rssi: int, pass_count, is_crossing):
        '''Parameter order must match order in packet'''
        node.current_rssi = RssiSample(timestamp, rssi)
        prev_pass_count = node.pass_count
        if prev_pass_count is None:
            # if None then initialize
            node.pass_count = pass_count
            node.lap_stats_status = DataStatus.NOT_AVAILABLE
            node.enter_stats_status = DataStatus.NOT_AVAILABLE
            node.exit_stats_status = DataStatus.NOT_AVAILABLE
        elif pass_count != prev_pass_count:
            if pass_count > prev_pass_count:
                if self.lap_count_change(pass_count, node.pass_count) > 1:
                    logger.warning("Missed pass on node {}!!! (count was {}, now is {})".format(node, node.pass_count, pass_count))
                if node.enter_stats_status != DataStatus.RETRIEVED:
                    node.enter_stats_status = DataStatus.AVAILABLE
                if node.exit_stats_status != DataStatus.RETRIEVED:
                    node.exit_stats_status = DataStatus.AVAILABLE
                node.lap_stats_status = DataStatus.AVAILABLE
            else:
                logger.warning("Resyncing lap counter for node {}!!! (count was {}, now is {})".format(node, node.pass_count, pass_count))
                node.pass_count = pass_count

        # if 'crossing' status changed
        if is_crossing != node.is_crossing:
            node.is_crossing = is_crossing
            if is_crossing:
                node.enter_stats_status = DataStatus.AVAILABLE
            else:
                if node.enter_stats_status != DataStatus.RETRIEVED:
                    node.enter_stats_status = DataStatus.AVAILABLE
                node.exit_stats_status = DataStatus.AVAILABLE

        self._notify_rssi_sample(node, timestamp, rssi)

        has_new_lap = (node.lap_stats_status == DataStatus.AVAILABLE)
        has_entered = (node.enter_stats_status == DataStatus.AVAILABLE)
        has_exited = (node.exit_stats_status == DataStatus.AVAILABLE)
        return has_new_lap, has_entered, has_exited

    def process_crossing(self, node, is_crossing, trigger_count, trigger_timestamp: int, trigger_rssi: int, trigger_lifetime: int):
        '''Parameter order must match order in packet'''
        logger.debug("{}: node={}, trigger_count={}, trigger_timestamp={}, trigger_rssi={}, trigger_lifetime={}".format("ENTER" if is_crossing else "EXIT", node, trigger_count, trigger_timestamp, trigger_rssi, trigger_lifetime))
        if is_crossing:
            if self.lap_count_change(trigger_count, node.pass_count) > 1:
                logger.warning("Missed enter on node {}!!! (count was {}, now is {})".format(node, node.pass_count, trigger_count))
            node.enter_stats_status = DataStatus.RETRIEVED
        else:
            if self.lap_count_change(trigger_count, node.pass_count) > 1:
                logger.warning("Missed exit on node {}!!! (count was {}, now is {})".format(node, node.pass_count, trigger_count))
            node.exit_stats_status = DataStatus.RETRIEVED

        # NB: crossing race times are relative to the race start time
        crossing_race_time = trigger_timestamp - self.race_start_time_ms
        if crossing_race_time < 0:
            logger.warning("Node {}: {} crossing before race start: {} < {}".format(node, "Enter" if is_crossing else "Exit", trigger_timestamp, self.race_start_time_ms))

        if is_crossing:
            node.pass_crossing_flag = True  # will be cleared when lap-pass is processed
            node.enter_at_sample = RssiSample(crossing_race_time, trigger_rssi)
            self._notify_enter_triggered(node, crossing_race_time, trigger_rssi, trigger_lifetime)
        else:
            node.exit_at_sample = RssiSample(crossing_race_time, trigger_rssi)
            self._notify_exit_triggered(node, crossing_race_time, trigger_rssi, trigger_lifetime)

    def process_lap_stats(self, node, pass_count, pass_timestamp: int, pass_peak_rssi: int, pass_nadir_rssi: int):
        '''Parameter order must match order in packet'''
        logger.debug("PASS: node={}, pass_count={}, pass_timestamp={}, pass_peak_rssi={}, pass_nadir_rssi={}".format(node, pass_count, pass_timestamp, pass_peak_rssi, pass_nadir_rssi))
        if self.lap_count_change(pass_count, node.pass_count) != 1:
            logger.warning("Missed pass on node {}!!! (count was {}, now is {})".format(node, node.pass_count, pass_count))
        node.pass_count = pass_count
        if pass_peak_rssi is not None:
            node.pass_peak_rssi = pass_peak_rssi
        if pass_nadir_rssi is not None:
            node.pass_nadir_rssi = pass_nadir_rssi
        if node.enter_stats_status == DataStatus.RETRIEVED and node.enter_at_sample.timestamp > pass_timestamp:
            logger.warning("Node {}: Enter timestamp {} is after pass timestamp {}!!! ".format(node, node.enter_at_sample.timestamp, pass_timestamp))
        if node.exit_stats_status == DataStatus.RETRIEVED and node.exit_at_sample.timestamp < pass_timestamp:
            logger.warning("Node {}: Exit timestamp {} is before pass timestamp {}!!! ".format(node, node.exit_at_sample.timestamp, pass_timestamp))
        node.is_crossing = False
        node.enter_at_sample = None
        node.exit_at_sample = None
        node.lap_stats_status = DataStatus.NOT_AVAILABLE
        node.enter_stats_status = DataStatus.NOT_AVAILABLE
        node.exit_stats_status = DataStatus.NOT_AVAILABLE

        # NB: lap race times are relative to the race start time
        lap_race_time_ms = pass_timestamp - self.race_start_time_ms
        if lap_race_time_ms < 0:
            logger.warning("Node {}: Lap before race start: {} < {}".format(node, pass_timestamp, self.race_start_time_ms))
        if self.is_racing and pass_peak_rssi:
            node.pass_history.append(RssiSample(pass_timestamp, pass_peak_rssi))

        self._notify_pass(node, lap_race_time_ms, BaseHardwareInterface.LAP_SOURCE_REALTIME, pass_peak_rssi)

    def process_rssi_stats(self, node, peak_rssi: int, nadir_rssi: int):
        '''Parameter order must match order in packet'''
        if peak_rssi is not None:
            node.node_peak_rssi = peak_rssi
        if nadir_rssi is not None:
            node.node_nadir_rssi = nadir_rssi

    def process_analytics(self, node, timestamp: int, lifetime: int, loop_time: int, extremum_rssi: int, extremum_timestamp: int, extremum_duration: int):
        '''Parameter order must match order in packet'''
        node.current_lifetime = LifetimeSample(timestamp, lifetime)
        self._notify_lifetime_sample(node, timestamp, lifetime)
        node.loop_time = loop_time
        if extremum_rssi is not None and extremum_timestamp is not None and extremum_duration is not None:
            self._notify_extremum_history(node, extremum_timestamp, extremum_rssi, extremum_duration)

    def append_history(self, node, timestamp: int, rssi: int, duration=0):
        # append history data (except when race is over)
        if self.is_racing:
            node.history.append(timestamp, rssi)
            if duration > 0:
                node.history.append(timestamp + duration, rssi)

            if rssi is not None:
                node.used_history_count += 1
            else:
                node.empty_history_count += 1

    def process_capturing(self, node):
        # check if capturing enter-at level for node
        if node.cap_enter_at_flag:
            node.cap_enter_at_total += node.current_rssi.rssi
            node.cap_enter_at_count += 1
            if ms_counter() >= node.cap_enter_at_end_ts_ms:
                node.enter_at_level = int(round(node.cap_enter_at_total / node.cap_enter_at_count))
                node.cap_enter_at_flag = False
                # if too close node peak then set a bit below node-peak RSSI value:
                if node.node_peak_rssi > 0 and node.node_peak_rssi - node.enter_at_level < ENTER_AT_PEAK_MARGIN:
                    node.enter_at_level = node.node_peak_rssi - ENTER_AT_PEAK_MARGIN
                logger.info('Finished capture of enter-at level for node {0}, level={1}, count={2}'.format(node, node.enter_at_level, node.cap_enter_at_count))
                self._notify_enter_trigger_changed(node)

        # check if capturing exit-at level for node
        if node.cap_exit_at_flag:
            node.cap_exit_at_total += node.current_rssi.rssi
            node.cap_exit_at_count += 1
            if ms_counter() >= node.cap_exit_at_end_ts_ms:
                node.exit_at_level = int(round(node.cap_exit_at_total / node.cap_exit_at_count))
                node.cap_exit_at_flag = False
                logger.info('Finished capture of exit-at level for node {0}, level={1}, count={2}'.format(node, node.exit_at_level, node.cap_exit_at_count))
                self._notify_exit_trigger_changed(node)

    def _restore_lowered_thresholds(self, node):
        # check if node is set to temporary lower EnterAt/ExitAt values
        if node.start_thresh_lower_flag and ms_counter() >= node.start_thresh_lower_time_ms:
            logger.info("For node {0} restoring EnterAt to {1} and ExitAt to {2}"\
                    .format(node.index+1, node.enter_at_level, \
                            node.exit_at_level))
            self.transmit_enter_at_level(node, node.enter_at_level)
            self.transmit_exit_at_level(node, node.exit_at_level)
            node.start_thresh_lower_flag = False
            node.start_thresh_lower_time_ms = 0

    def ai_calibrate_nodes(self):
        for node in self.nodes:
            history_times, history_values = node.history.get()
            assert len(history_times) == len(history_values)
            if node.ai_calibrate and node.first_cross_flag and history_values:
                ccs = ph.calculatePeakPersistentHomology(history_values)
                lo, hi = ph.findBreak(ccs)
                diff = hi - lo
                if diff > 1:
                    # cap changes to 50%
                    learning_rate = 0.5
                    new_enter_level = int((lo + diff/2 - node.enter_at_level)*learning_rate + node.enter_at_level)
                    # set exit a bit lower to register a pass sooner
                    new_exit_level = int((lo + diff/4 - node.exit_at_level)*learning_rate + node.exit_at_level)
                    logger.info('AI calibrating node {}: break {}-{}, adjusting ({}, {}) to ({}, {})'.format(node.index, lo, hi, node.enter_at_level, node.exit_at_level, new_enter_level, new_exit_level))
                    node.enter_at_level = new_enter_level
                    node.exit_at_level = new_exit_level
                    self._notify_enter_trigger_changed(node)
                    self._notify_exit_trigger_changed(node)
                else:
                    logger.info('AI calibrating node {}: break {}-{} too narrow'.format(node.index, lo, hi))

    def calibrate_nodes(self, start_time_ms: int, race_laps_history: Dict[int,Tuple[List[Dict[str,Any]],List[int],List[int]]]):
        for node_idx, node_laps_history in race_laps_history.items():
            node = self.nodes[node_idx]
            node_laps, history_times, history_values = node_laps_history
            assert len(history_times) == len(history_values)
            if node.calibrate and history_values:
                lap_ts_ms = [start_time_ms + lap['lap_time_stamp'] for lap in node_laps if not lap['deleted']]
                if lap_ts_ms:
                    ccs = ph.calculatePeakPersistentHomology(history_values)
                    ccs.sort(key=lambda cc: history_times[cc.birth[0]])
                    birth_ts = [history_times[cc.birth[0]] for cc in ccs]
                    pass_idxs = []
                    for lap_timestamp in lap_ts_ms:
                        idx = bisect.bisect_left(birth_ts, lap_timestamp)
                        if idx == len(birth_ts):
                            pass_idxs.append(idx-1)
                        elif idx == 0 or birth_ts[idx] == lap_timestamp:
                            pass_idxs.append(idx)
                        elif ccs[idx].lifetime() > ccs[idx-1].lifetime():
                            pass_idxs.append(idx)
                        else:
                            pass_idxs.append(idx-1)
                    hi = min([ccs[j].lifetime() for j in pass_idxs])
                    lo = max([cc.lifetime() for cc in ccs if cc.lifetime() < hi]+[0])
                    diff = hi - lo
                    if diff > 1:
                        new_enter_level = lo + diff//2
                        new_exit_level = lo + diff//4
                        logger.info('Calibrating node {}: break {}-{}, adjusting ({}, {}) to ({}, {})'.format(node.index, lo, hi, node.enter_at_level, node.exit_at_level, new_enter_level, new_exit_level))
                        node.enter_at_level = new_enter_level
                        node.exit_at_level = new_exit_level
                        self._notify_enter_trigger_changed(node)
                        self._notify_exit_trigger_changed(node)
                    else:
                        logger.info('Calibrating node {}: break {}-{} too narrow'.format(node.index, lo, hi))

    def transmit_frequency(self, node, frequency):
        return frequency

    def transmit_enter_at_level(self, node, level):
        return level

    def transmit_exit_at_level(self, node, level):
        return level

    #
    # External functions for setting data
    #

    def simulate_lap(self, node_index):
        node = self.nodes[node_index]
        lap_race_time_ms = ms_counter() - self.race_start_time_ms  # relative to start time
        node.enter_at_sample = node.exit_at_sample = None
        self._notify_pass(node, lap_race_time_ms, BaseHardwareInterface.LAP_SOURCE_MANUAL, None)

    def force_end_crossing(self, node_index):
        pass

    def on_race_start(self, race_start_time_ms: int):
        for node in self.nodes:
            node.reset()
        self.race_start_time_ms = race_start_time_ms
        self.is_racing = True

    def on_race_stop(self):
        self.is_racing = False
        for node in self.nodes:
            node.history.merge(node.pass_history)
            node.pass_history = []
        gevent.spawn(self.ai_calibrate_nodes)
        for node in self.nodes:
            node.summary_stats()

    def set_frequency(self, node_index, frequency, band=None, channel=None):
        node = self.nodes[node_index]
        old_frequency = node.frequency
        old_bandChannel = node.bandChannel
        if frequency != old_frequency:
            node.debug_pass_count = 0  # reset debug pass count on frequency change
            disabled_freq = node.manager.get_disabled_frequency()
            # if frequency == 0 (node disabled) then write frequency value to power down rx module, but save 0 value
            _freq = frequency if frequency else disabled_freq
            new_freq = self.transmit_frequency(node, _freq)
            if frequency or new_freq != disabled_freq:
                node.frequency = new_freq
            else:
                node.frequency = 0
            # if node enabled and successfully changed frequency and have an associated band/channel
            if frequency and new_freq == _freq and band and channel:
                node.bandChannel = band + str(channel)
            else:
                node.bandChannel = None
        else:
            # just changing band/channel values
            if band and channel:
                node.bandChannel = band + str(channel)
        if node.frequency != old_frequency or node.bandChannel != old_bandChannel:
            self._notify_frequency_changed(node)

    def set_enter_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.is_valid_rssi(level):
            old_level = node.enter_at_level
            node.enter_at_level = self.transmit_enter_at_level(node, level)
            if node.enter_at_level != old_level:
                self._notify_enter_trigger_changed(node)

    def set_exit_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.is_valid_rssi(level):
            old_level = node.exit_at_level
            node.exit_at_level = self.transmit_exit_at_level(node, level)
            if node.exit_at_level != old_level:
                self._notify_exit_trigger_changed(node)

    def start_capture_enter_at_level(self, node_index):
        node = self.nodes[node_index]
        if node.cap_enter_at_flag is False:
            node.cap_enter_at_total = 0
            node.cap_enter_at_count = 0
            # set end time for capture of RSSI level:
            node.cap_enter_at_end_ts_ms = ms_counter() + CAP_ENTER_EXIT_AT_MS
            node.cap_enter_at_flag = True
            return True
        return False

    def start_capture_exit_at_level(self, node_index):
        node = self.nodes[node_index]
        if node.cap_exit_at_flag is False:
            node.cap_exit_at_total = 0
            node.cap_exit_at_count = 0
            # set end time for capture of RSSI level:
            node.cap_exit_at_end_ts_ms = ms_counter() + CAP_ENTER_EXIT_AT_MS
            node.cap_exit_at_flag = True
            return True
        return False

    def get_node_frequencies(self):
        return [node.frequency if not node.scan_enabled else FREQUENCY_ID_NONE for node in self.nodes]

    #
    # Get Json Node Data Functions
    #

    def get_heartbeat_json(self):
        json = {
            'current_rssi': [node.current_rssi.rssi if not node.scan_enabled else 0 for node in self.nodes],
            'current_lifetime': [node.current_lifetime.lifetime if not node.scan_enabled else 0 for node in self.nodes],
            'frequency': self.get_node_frequencies(),
            'loop_time': [node.loop_time if not node.scan_enabled else 0 for node in self.nodes],
            'crossing_flag': [node.is_crossing if not node.scan_enabled else False for node in self.nodes]
        }
        return json

    def get_frequency_json(self, node_index):
        node = self.nodes[node_index]
        return {
            'node': node.index,
            'frequency': node.frequency
        }

    @property
    def intf_read_command_count(self):
        total = 0
        for manager in self.node_managers:
            total += manager.read_command_count
        for node in self.nodes:
            total += node.read_command_count
        return total

    @property
    def intf_read_error_count(self):
        total = 0
        for manager in self.node_managers:
            total += manager.read_error_count
        for node in self.nodes:
            total += node.read_error_count
        return total

    @property
    def intf_write_command_count(self):
        total = 0
        for manager in self.node_managers:
            total += manager.write_command_count
        for node in self.nodes:
            total += node.write_command_count
        return total

    @property
    def intf_write_error_count(self):
        total = 0
        for manager in self.node_managers:
            total += manager.write_error_count
        for node in self.nodes:
            total += node.write_error_count
        return total

    def get_intf_total_error_count(self):
        return self.intf_read_error_count + self.intf_write_error_count

    # log comm errors if error percentage is >= this value
    def set_intf_error_report_percent_limit(self, percentVal):
        self.intf_error_report_limit = percentVal / 100

    def get_intf_error_report_str(self, forceFlag=False):
        try:
            if self.intf_read_command_count <= 0:
                return None
            r_err_ratio = float(self.intf_read_error_count) / float(self.intf_read_command_count) \
                          if self.intf_read_error_count > 0 else 0
            w_err_ratio = float(self.intf_write_error_count) / float(self.intf_write_command_count) \
                          if self.intf_write_command_count > 0 and self.intf_write_error_count > 0 else 0
            if forceFlag or r_err_ratio > self.intf_error_report_limit or \
                                        w_err_ratio > self.intf_error_report_limit:
                retStr = "CommErrors:"
                if forceFlag or self.intf_write_error_count > 0:
                    retStr += "Write:{0}/{1}({2:.2%}),".format(self.intf_write_error_count,
                                    self.intf_write_command_count, w_err_ratio)
                retStr += "Read:{0}/{1}({2:.2%})".format(self.intf_read_error_count,
                                    self.intf_read_command_count, r_err_ratio)
                for node in self.nodes:
                    retStr += ", " + node.get_read_error_report_str()
                return retStr
        except Exception as ex:
            logger.info("Error in 'get_intf_error_report_str()': " + str(ex))
        return None
