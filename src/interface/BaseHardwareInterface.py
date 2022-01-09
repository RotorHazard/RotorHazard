import os
import gevent
import logging
from monotonic import monotonic
import util.persistent_homology as ph
from server.RHUtils import FREQUENCY_ID_NONE
import bisect

ENTER_AT_PEAK_MARGIN = 5  # closest that captured enter-at level can be to node peak RSSI
CAP_ENTER_EXIT_AT_MILLIS = 3000  # number of ms for capture of enter/exit-at levels

logger = logging.getLogger(__name__)


class BaseHardwareInterfaceListener:
    def on_enter_triggered(self, node):
        pass

    def on_exit_triggered(self, node):
        pass

    def on_pass(self, node, lap_ts, lap_source):
        pass

    def on_frequency_changed(self, node, frequency, band=None, channel=None):
        pass

    def on_enter_trigger_changed(self, node, level):
        pass

    def on_exit_trigger_changed(self, node, level):
        pass


class BaseHardwareInterface:

    LAP_SOURCE_REALTIME = 0
    LAP_SOURCE_MANUAL = 1
    LAP_SOURCE_RECALC = 2

    RACE_STATUS_READY = 0
    RACE_STATUS_RACING = 1
    RACE_STATUS_DONE = 2

    def __init__(self, listener=None, update_sleep=0.1):
        self.node_managers = []
        self.nodes = []
        # Main update loop delay
        self.update_sleep = float(os.environ.get('RH_UPDATE_INTERVAL', update_sleep))
        self.update_thread = None  # Thread for running the main update loop
        self.start_time = None  # millis
        self.environmental_data_update_tracker = 0
        self.race_start_time = 0
        self.is_racing = False
        self.listener = listener if listener is not None else BaseHardwareInterfaceListener()
        self.intf_error_report_limit = 0.0  # log if ratio of comm errors is larger

    def milliseconds(self):
        '''
        Returns the elapsed milliseconds since this interface was started.
        '''
        return 1000*monotonic() - self.start_time if self.start_time is not None else None

    def start(self):
        if self.update_thread is None:
            logger.info('Starting {} background thread'.format(type(self).__name__))
            self.update_thread = gevent.spawn(self._update_loop)
            self.start_time = 1000*monotonic()  # millis

    def stop(self):
        if self.update_thread:
            logger.info('Stopping {} background thread'.format(type(self).__name__))
            self.update_thread.kill(block=True, timeout=0.5)
            self.update_thread = None
            self.start_time = None

    def close(self):
        for node in self.nodes:
            node.summary_stats()
        for manager in self.node_managers:
            manager.close()

    def _notify_enter_triggered(self, node):
        self.listener.on_enter_triggered(node)

    def _notify_exit_triggered(self, node):
        self.listener.on_exit_triggered(node)

    def _notify_pass(self, node, lap_ts, lap_source):
        self.listener.on_pass(node, lap_ts, lap_source)

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

    def process_lap_stats(self, node, readtime, lap_id, ms_val, cross_flag, pn_history):
        crossing_updated = False
        new_lap = False
        if cross_flag is not None and cross_flag != node.crossing_flag:  # if 'crossing' status changed
            node.crossing_flag = cross_flag
            if cross_flag:
                node.pass_crossing_flag = True  # will be cleared when lap-pass is processed
                node.enter_at_timestamp = readtime
            else:
                node.exit_at_timestamp = readtime
            crossing_updated = True

        # calc lap timestamp
        if ms_val < 0 or ms_val > 9999999:
            ms_val = 0  # don't allow negative or too-large value
            lap_timestamp = 0
        else:
            lap_timestamp = readtime - (ms_val / 1000.0)

        # if new lap detected for node then append item to updates list
        prev_lap_id = node.node_lap_id
        if lap_id != prev_lap_id:
            node.node_lap_id = lap_id
            if prev_lap_id != -1:  # if -1 then just initialising node_lap_id
                if lap_id != prev_lap_id + 1:
                    logger.warning("Missed lap!!! (lap ID was {}, now is {})".format(prev_lap_id, lap_id))
                if self.is_racing:
                    node.pass_history.append((lap_timestamp, node.pass_peak_rssi))
                new_lap = True

        if crossing_updated:
            if node.crossing_flag:
                self._notify_enter_triggered(node)
            else:
                self._notify_exit_triggered(node)
        if new_lap:
            # NB: lap pass timestamps are relative to race start time
            self._notify_pass(node, lap_timestamp - self.race_start_time, BaseHardwareInterface.LAP_SOURCE_REALTIME)

        # check if capturing enter-at level for node
        if node.cap_enter_at_flag:
            node.cap_enter_at_total += node.current_rssi
            node.cap_enter_at_count += 1
            if self.milliseconds() >= node.cap_enter_at_millis:
                node.enter_at_level = int(round(node.cap_enter_at_total / node.cap_enter_at_count))
                node.cap_enter_at_flag = False
                # if too close node peak then set a bit below node-peak RSSI value:
                if node.node_peak_rssi > 0 and node.node_peak_rssi - node.enter_at_level < ENTER_AT_PEAK_MARGIN:
                    node.enter_at_level = node.node_peak_rssi - ENTER_AT_PEAK_MARGIN
                logger.info('Finished capture of enter-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.enter_at_level, node.cap_enter_at_count))
                self._notify_enter_trigger_changed(node)

        # check if capturing exit-at level for node
        if node.cap_exit_at_flag:
            node.cap_exit_at_total += node.current_rssi
            node.cap_exit_at_count += 1
            if self.milliseconds() >= node.cap_exit_at_millis:
                node.exit_at_level = int(round(node.cap_exit_at_total / node.cap_exit_at_count))
                node.cap_exit_at_flag = False
                logger.info('Finished capture of exit-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.exit_at_level, node.cap_exit_at_count))
                self._notify_exit_trigger_changed(node)

        self.prune_history(node)

        # get and process history data (except when race is over)
        if pn_history and self.is_racing:
            if not pn_history.isEmpty():
                pn_history.addTo(readtime, node.history)
                node.used_history_count += 1
            else:
                node.empty_history_count += 1

    def prune_history(self, node):
        # prune history data if race is not running (keep last 60s)
        if not self.is_racing:
            node.history.prune(monotonic()-60)

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

    def calibrate_nodes(self, start_time, race_laps_history):
        for node_idx, node_laps_history in race_laps_history.items():
            node = self.nodes[node_idx]
            node_laps, history_times, history_values = node_laps_history
            assert len(history_times) == len(history_values)
            if node.calibrate and history_values:
                lap_ts = [start_time + lap['lap_time_stamp']/1000 for lap in node_laps if not lap['deleted']]
                if lap_ts:
                    ccs = ph.calculatePeakPersistentHomology(history_values)
                    ccs.sort(key=lambda cc: history_times[cc.birth[0]])
                    birth_ts = [history_times[cc.birth[0]] for cc in ccs]
                    pass_idxs = []
                    for lap_timestamp in lap_ts:
                        idx = bisect.bisect_left(birth_ts, lap_timestamp)
                        if idx == 0 or birth_ts[idx] == lap_timestamp:
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
        lap_timestamp = monotonic() - self.race_start_time  # relative to start time
        node.enter_at_timestamp = node.exit_at_timestamp = 0
        node.node_lap_id += 1
        self._notify_pass(node, lap_timestamp, BaseHardwareInterface.LAP_SOURCE_MANUAL)

    def force_end_crossing(self, node_index):
        pass

    def on_race_start(self):
        for node in self.nodes:
            node.reset()
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
            node.cap_enter_at_millis = self.milliseconds() + CAP_ENTER_EXIT_AT_MILLIS
            node.cap_enter_at_flag = True
            return True
        return False

    def start_capture_exit_at_level(self, node_index):
        node = self.nodes[node_index]
        if node.cap_exit_at_flag is False:
            node.cap_exit_at_total = 0
            node.cap_exit_at_count = 0
            # set end time for capture of RSSI level:
            node.cap_exit_at_millis = self.milliseconds() + CAP_ENTER_EXIT_AT_MILLIS
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
            'current_rssi': [node.current_rssi if not node.scan_enabled else 0 for node in self.nodes],
            'frequency': self.get_node_frequencies(),
            'loop_time': [node.loop_time if not node.scan_enabled else 0 for node in self.nodes],
            'crossing_flag': [node.crossing_flag if not node.scan_enabled else False for node in self.nodes]
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


class PeakNadirHistory:
    def __init__(self, node_index=-1):
        self.nodeIndex = node_index
        self.peakRssi = 0
        self.peakFirstTime = 0
        self.peakLastTime = 0
        self.nadirRssi = 0
        self.nadirFirstTime = 0
        self.nadirLastTime = 0

    def isEmpty(self):
        return self.peakRssi == 0 and self.peakFirstTime == 0 and self.peakLastTime == 0 \
            and self.nadirRssi == 0 and self.nadirFirstTime == 0 and self.nadirLastTime == 0

    def addTo(self, readtime, history):
        if self.peakRssi > 0:
            if self.nadirRssi > 0:
                # both
                if self.peakLastTime > self.nadirFirstTime:
                    # process peak first
                    if self.peakFirstTime > self.peakLastTime:
                        history.append(readtime - (self.peakFirstTime / 1000.0), self.peakRssi)
                        history.append(readtime - (self.peakLastTime / 1000.0), self.peakRssi)
                    elif self.peakFirstTime == self.peakLastTime:
                        history.append(readtime - (self.peakLastTime / 1000.0), self.peakRssi)
                    else:
                        logger.warning('Ignoring corrupted peak history times ({0} < {1}) on node {2}'.format(self.peakFirstTime, self.peakLastTime, self.nodeIndex+1))

                    if self.nadirFirstTime > self.nadirLastTime:
                        history.append(readtime - (self.nadirFirstTime / 1000.0), self.nadirRssi)
                        history.append(readtime - (self.nadirLastTime / 1000.0), self.nadirRssi)
                    elif self.nadirFirstTime == self.nadirLastTime:
                        history.append(readtime - (self.nadirLastTime / 1000.0), self.nadirRssi)
                    else:
                        logger.warning('Ignoring corrupted nadir history times ({0} < {1}) on node {2}'.format(self.nadirFirstTime, self.nadirLastTime, self.nodeIndex+1))

                else:
                    # process nadir first
                    if self.nadirFirstTime > self.nadirLastTime:
                        history.append(readtime - (self.nadirFirstTime / 1000.0), self.nadirRssi)
                        history.append(readtime - (self.nadirLastTime / 1000.0), self.nadirRssi)
                    elif self.nadirFirstTime == self.nadirLastTime:
                        history.append(readtime - (self.nadirLastTime / 1000.0), self.nadirRssi)
                    else:
                        logger.warning('Ignoring corrupted nadir history times ({0} < {1}) on node {2}'.format(self.nadirFirstTime, self.nadirLastTime, self.nodeIndex+1))

                    if self.peakFirstTime > self.peakLastTime:
                        history.append(readtime - (self.peakFirstTime / 1000.0), self.peakRssi)
                        history.append(readtime - (self.peakLastTime / 1000.0), self.peakRssi)
                    elif self.peakFirstTime == self.peakLastTime:
                        history.append(readtime - (self.peakLastTime / 1000.0), self.peakRssi)
                    else:
                        logger.warning('Ignoring corrupted peak history times ({0} < {1}) on node {2}'.format(self.peakFirstTime, self.peakLastTime, self.nodeIndex+1))

            else:
                # peak, no nadir
                # process peak only
                if self.peakFirstTime > self.peakLastTime:
                    history.append(readtime - (self.peakFirstTime / 1000.0), self.peakRssi)
                    history.append(readtime - (self.peakLastTime / 1000.0), self.peakRssi)
                elif self.peakFirstTime == self.peakLastTime:
                    history.append(readtime - (self.peakLastTime / 1000.0), self.peakRssi)
                else:
                    logger.warning('Ignoring corrupted peak history times ({0} < {1}) on node {2}'.format(self.peakFirstTime, self.peakLastTime, self.nodeIndex+1))

        elif self.nadirRssi > 0:
            # no peak, nadir
            # process nadir only
            if self.nadirFirstTime > self.nadirLastTime:
                history.append(readtime - (self.nadirFirstTime / 1000.0), self.nadirRssi)
                history.append(readtime - (self.nadirLastTime / 1000.0), self.nadirRssi)
            elif self.nadirFirstTime == self.nadirLastTime:
                history.append(readtime - (self.nadirLastTime / 1000.0), self.nadirRssi)
            else:
                logger.warning('Ignoring corrupted nadir history times ({0} < {1}) on node {2}'.format(self.nadirFirstTime, self.nadirLastTime, self.nodeIndex+1))
