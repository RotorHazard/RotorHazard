import os
import gevent
import logging
from monotonic import monotonic
from interface import persistent_homology as ph
import bisect

FREQUENCY_NONE = 0
ENTER_AT_PEAK_MARGIN = 5 # closest that captured enter-at level can be to node peak RSSI
CAP_ENTER_EXIT_AT_MILLIS = 3000  # number of ms for capture of enter/exit-at levels

logger = logging.getLogger(__name__)


class BaseHardwareInterface:

    LAP_SOURCE_REALTIME = 0
    LAP_SOURCE_MANUAL = 1
    LAP_SOURCE_RECALC = 2

    RACE_STATUS_READY = 0
    RACE_STATUS_STAGING = 3
    RACE_STATUS_RACING = 1
    RACE_STATUS_DONE = 2

    def __init__(self, update_sleep=0.1):
        self.node_managers = []
        self.nodes = []
        # Main update loop delay
        self.update_sleep = float(os.environ.get('RH_UPDATE_INTERVAL', update_sleep))
        self.update_thread = None # Thread for running the main update loop
        self.start_time = 1000*monotonic() # millis
        self.environmental_data_update_tracker = 0
        self.race_start_time = 0
        self.race_status = BaseHardwareInterface.RACE_STATUS_READY
        self.pass_record_callback = None # Function added in server.py
        self.new_enter_or_exit_at_callback = None # Function added in server.py
        self.node_crossing_callback = None # Function added in server.py
        self.intf_error_report_limit = 0.0  # log if ratio of comm errors is larger

    # returns the elapsed milliseconds since the start of the program
    def milliseconds(self):
        return 1000*monotonic() - self.start_time

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
        for manager in self.node_managers:
            manager.close()

    def _update_loop(self):
        while True:
            try:
                self._update()
                gevent.sleep(self.update_sleep)
            except KeyboardInterrupt:
                logger.info("Update thread terminated by keyboard interrupt")
                raise
            except OSError:
                raise
            except SystemExit:
                raise
            except Exception:
                logger.exception('Exception in {} _update_loop():'.format(type(self).__name__))
                gevent.sleep(self.update_sleep*10)

    def process_lap_stats(self, node, readtime, lap_id, ms_val, cross_flag, pn_history, cross_list, upd_list):
        if cross_flag is not None and cross_flag != node.crossing_flag:  # if 'crossing' status changed
            node.crossing_flag = cross_flag
            if cross_flag:
                node.pass_crossing_flag = True  # will be cleared when lap-pass is processed
                node.enter_at_timestamp = monotonic()
            else:
                node.exit_at_timestamp = monotonic()
            if callable(self.node_crossing_callback):
                cross_list.append(node)

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
            if prev_lap_id != -1: # if -1 then just initialising node_lap_id
                if lap_id != prev_lap_id + 1:
                    logger.warning("Missed lap!!! (lap ID was {}, now is {})".format(prev_lap_id, lap_id))
                if self.race_status == BaseHardwareInterface.RACE_STATUS_RACING:
                    node.pass_history.append((lap_timestamp, node.pass_peak_rssi))
                # NB: update lap timestamps are relative to start time
                upd_list.append((node, lap_timestamp - self.race_start_time))

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
                if callable(self.new_enter_or_exit_at_callback):
                    gevent.spawn(self.new_enter_or_exit_at_callback, node.index, enter_at_level=node.enter_at_level)

        # check if capturing exit-at level for node
        if node.cap_exit_at_flag:
            node.cap_exit_at_total += node.current_rssi
            node.cap_exit_at_count += 1
            if self.milliseconds() >= node.cap_exit_at_millis:
                node.exit_at_level = int(round(node.cap_exit_at_total / node.cap_exit_at_count))
                node.cap_exit_at_flag = False
                logger.info('Finished capture of exit-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.exit_at_level, node.cap_exit_at_count))
                if callable(self.new_enter_or_exit_at_callback):
                    gevent.spawn(self.new_enter_or_exit_at_callback, node.index, exit_at_level=node.exit_at_level)

        self.prune_history(node)

        # get and process history data (except when race is over)
        if pn_history and self.race_status != BaseHardwareInterface.RACE_STATUS_DONE:
            if not pn_history.isEmpty():
                pn_history.addTo(readtime, node.history_values, node.history_times)
                node.used_history_count += 1
            else:
                node.empty_history_count += 1

    def prune_history(self, node):
        # prune history data if race is not running (keep last 60s)
        if self.race_status == BaseHardwareInterface.RACE_STATUS_READY:
            prune_idx = bisect.bisect_left(node.history_times, monotonic()-60)
            del node.history_values[:prune_idx]
            del node.history_times[:prune_idx]

    def process_crossings(self, cross_list):
        '''
        cross_list - list of node objects
        '''
        if len(cross_list) > 0 and callable(self.node_crossing_callback):
            gevent.spawn(self._process_crossings, cross_list)

    def _process_crossings(self, cross_list):
        for node in cross_list:
            self.node_crossing_callback(node)

    def process_updates(self, upd_list):
        '''
        upd_list - list of (node, lap_timestamp) tuples
        '''
        if len(upd_list) > 0 and callable(self.pass_record_callback):
            gevent.spawn(self._process_updates, upd_list)

    def _process_updates(self, upd_list):
        if len(upd_list) == 1:  # list contains single item
            item = upd_list[0]
            node = item[0]
            lap_timestamp = item[1]
            self.pass_record_callback(node, lap_timestamp, BaseHardwareInterface.LAP_SOURCE_REALTIME)

        elif len(upd_list) > 1:  # list contains multiple items; sort so processed in order by lap time
            upd_list.sort(key = lambda i: i[1])
            for item in upd_list:
                node = item[0]
                lap_timestamp = item[1]
                self.pass_record_callback(node, lap_timestamp, BaseHardwareInterface.LAP_SOURCE_REALTIME)

    def ai_calibrate_nodes(self):
        for node in self.nodes:
            if node.ai_calibrate and node.first_cross_flag and node.history_values:
                ccs = ph.calculatePeakPersistentHomology(node.history_values)
                lo, hi = ph.findBreak(ccs)
                diff = hi - lo
                if diff > 1:
                    # cap changes to 50%
                    learning_rate = 0.5
                    enter_level = int((lo + diff/2 - node.enter_at_level)*learning_rate + node.enter_at_level)
                    # set exit a bit lower to register a pass sooner
                    exit_level = int((lo + diff/4 - node.exit_at_level)*learning_rate + node.exit_at_level)
                    logger.info('AI calibrating node {}: break {}-{}, adjusting ({}, {}) to ({}, {})'.format(node.index, lo, hi, node.enter_at_level, node.exit_at_level, enter_level, exit_level))
                    if callable(self.new_enter_or_exit_at_callback):
                        self.new_enter_or_exit_at_callback(node.index, enter_level, exit_level)
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
                    lo = max([cc.lifetime() for cc in ccs if cc.lifetime()<hi]+[0])
                    diff = hi - lo
                    if diff > 1:
                        enter_level = lo + diff//2
                        exit_level = lo + diff//4
                        logger.info('Calibrating node {}: break {}-{}, adjusting ({}, {}) to ({}, {})'.format(node.index, lo, hi, node.enter_at_level, node.exit_at_level, enter_level, exit_level))
                        if callable(self.new_enter_or_exit_at_callback):
                            self.new_enter_or_exit_at_callback(node.index, enter_level, exit_level)
                    else:
                        logger.info('Calibrating node {}: break {}-{} too narrow'.format(node.index, lo, hi))

    #
    # External functions for setting data
    #

    def intf_simulate_lap(self, node_index, ms_val):
        node = self.nodes[node_index]
        lap_timestamp = monotonic() - (ms_val / 1000.0) - self.race_start_time # relative to start time
        node.enter_at_timestamp = node.exit_at_timestamp = 0
        gevent.spawn(self.pass_record_callback, node, lap_timestamp, BaseHardwareInterface.LAP_SOURCE_MANUAL)

    def set_race_status(self, race_status):
        self.race_status = race_status
        if race_status == BaseHardwareInterface.RACE_STATUS_DONE:
            for node in self.nodes:
                node.consolidate_history()
            gevent.spawn(self.ai_calibrate_nodes)
            msg = ['RSSI history buffering utilisation:']
            for node in self.nodes:
                total_count = node.used_history_count + node.empty_history_count
                msg.append("\tNode {} {:.2%}".format(node, node.used_history_count/total_count if total_count > 0 else 0))
            logger.debug('\n'.join(msg))

    def set_enter_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.is_valid_rssi(level):
            if self.transmit_enter_at_level(node, level):
                node.enter_at_level = level

    def set_exit_at_level(self, node_index, level):
        node = self.nodes[node_index]
        if node.is_valid_rssi(level):
            if self.transmit_exit_at_level(node, level):
                node.exit_at_level = level

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
        return [node.frequency if not node.scan_enabled else FREQUENCY_NONE for node in self.nodes]

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
        self.intf_error_report_limit = percentVal / 100;

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
                    retStr += "Write:{0}/{1}({2:.2%}),".format(self.intf_write_error_count, \
                                    self.intf_write_command_count, w_err_ratio)
                retStr += "Read:{0}/{1}({2:.2%})".format(self.intf_read_error_count, \
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

    def addTo(self, readtime, history_values, history_times):
        if self.peakRssi > 0:
            if self.nadirRssi > 0:
                # both
                if self.peakLastTime > self.nadirFirstTime:
                    # process peak first
                    if self.peakFirstTime > self.peakLastTime:
                        self._addEntry(self.peakRssi, readtime - (self.peakFirstTime / 1000.0), history_values, history_times)
                        self._addEntry(self.peakRssi, readtime - (self.peakLastTime / 1000.0), history_values, history_times)
                    elif self.peakFirstTime == self.peakLastTime:
                        self._addEntry(self.peakRssi, readtime - (self.peakLastTime / 1000.0), history_values, history_times)
                    else:
                        logger.warning('Ignoring corrupted peak history times ({0} < {1}) on node {2}'.format(self.peakFirstTime, self.peakLastTime, self.nodeIndex+1))

                    if self.nadirFirstTime > self.nadirLastTime:
                        self._addEntry(self.nadirRssi, readtime - (self.nadirFirstTime / 1000.0), history_values, history_times)
                        self._addEntry(self.nadirRssi, readtime - (self.nadirLastTime / 1000.0), history_values, history_times)
                    elif self.nadirFirstTime == self.nadirLastTime:
                        self._addEntry(self.nadirRssi, readtime - (self.nadirLastTime / 1000.0), history_values, history_times)
                    else:
                        logger.warning('Ignoring corrupted nadir history times ({0} < {1}) on node {2}'.format(self.nadirFirstTime, self.nadirLastTime, self.nodeIndex+1))

                else:
                    # process nadir first
                    if self.nadirFirstTime > self.nadirLastTime:
                        self._addEntry(self.nadirRssi, readtime - (self.nadirFirstTime / 1000.0), history_values, history_times)
                        self._addEntry(self.nadirRssi, readtime - (self.nadirLastTime / 1000.0), history_values, history_times)
                    elif self.nadirFirstTime == self.nadirLastTime:
                        self._addEntry(self.nadirRssi, readtime - (self.nadirLastTime / 1000.0), history_values, history_times)
                    else:
                        logger.warning('Ignoring corrupted nadir history times ({0} < {1}) on node {2}'.format(self.nadirFirstTime, self.nadirLastTime, self.nodeIndex+1))

                    if self.peakFirstTime > self.peakLastTime:
                        self._addEntry(self.peakRssi, readtime - (self.peakFirstTime / 1000.0), history_values, history_times)
                        self._addEntry(self.peakRssi, readtime - (self.peakLastTime / 1000.0), history_values, history_times)
                    elif self.peakFirstTime == self.peakLastTime:
                        self._addEntry(self.peakRssi, readtime - (self.peakLastTime / 1000.0), history_values, history_times)
                    else:
                        logger.warning('Ignoring corrupted peak history times ({0} < {1}) on node {2}'.format(self.peakFirstTime, self.peakLastTime, self.nodeIndex+1))

            else:
                # peak, no nadir
                # process peak only
                if self.peakFirstTime > self.peakLastTime:
                    self._addEntry(self.peakRssi, readtime - (self.peakFirstTime / 1000.0), history_values, history_times)
                    self._addEntry(self.peakRssi, readtime - (self.peakLastTime / 1000.0), history_values, history_times)
                elif self.peakFirstTime == self.peakLastTime:
                    self._addEntry(self.peakRssi, readtime - (self.peakLastTime / 1000.0), history_values, history_times)
                else:
                    logger.warning('Ignoring corrupted peak history times ({0} < {1}) on node {2}'.format(self.peakFirstTime, self.peakLastTime, self.nodeIndex+1))

        elif self.nadirRssi > 0:
            # no peak, nadir
            # process nadir only
            if self.nadirFirstTime > self.nadirLastTime:
                self._addEntry(self.nadirRssi, readtime - (self.nadirFirstTime / 1000.0), history_values, history_times)
                self._addEntry(self.nadirRssi, readtime - (self.nadirLastTime / 1000.0), history_values, history_times)
            elif self.nadirFirstTime == self.nadirLastTime:
                self._addEntry(self.nadirRssi, readtime - (self.nadirLastTime / 1000.0), history_values, history_times)
            else:
                logger.warning('Ignoring corrupted nadir history times ({0} < {1}) on node {2}'.format(self.nadirFirstTime, self.nadirLastTime, self.nodeIndex+1))

    def _addEntry(self, entry_value, entry_time, history_values, history_times):
        hist_len = len(history_values)
        # if previous two entries have same value then just extend time on last entry
        if hist_len >= 2 and history_values[hist_len-1] == entry_value and history_values[hist_len-2] == entry_value:
            history_times[hist_len-1] = entry_time
        else:
            history_values.append(entry_value)
            history_times.append(entry_time)
