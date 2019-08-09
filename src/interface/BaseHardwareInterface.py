import importlib
import pkgutil
from monotonic import monotonic

ENTER_AT_PEAK_MARGIN = 5 # closest that captured enter-at level can be to node peak RSSI


def discover_modules(type):
    plugin_modules = []
    for loader, name, ispkg in pkgutil.iter_modules():
        if name.endswith('_'+type):
            try:
                plugin_module = importlib.import_module(name)
                plugin_modules.append(plugin_module)
                print('Loaded module {0}'.format(name))
            except ImportError:
                pass
    return plugin_modules

def discover_plugins(type, *args, **kwargs):
    plugins = []
    for plugin_module in discover_modules(type):
        try:
            plugins.extend(plugin_module.discover(*args, **kwargs))
        except AttributeError as err:
            print('Error loading plugin {0}: {1}'.format(plugin_module.__name__, err))
            pass
    return plugins


class BaseHardwareInterface(object):

    LAP_SOURCE_REALTIME = 0
    LAP_SOURCE_MANUAL = 1
    LAP_SOURCE_RECALC = 2

    RACE_STATUS_READY = 0
    RACE_STATUS_STAGING = 3
    RACE_STATUS_RACING = 1
    RACE_STATUS_DONE = 2

    def __init__(self):
        self.calibration_threshold = 20
        self.calibration_offset = 10
        self.trigger_threshold = 20
        self.start_time = 1000*monotonic() # millis
        self.sensors = []
        self.environmental_data_update_tracker = 0
        self.race_status = BaseHardwareInterface.RACE_STATUS_READY

    def discover_sensors(self, *args, **kwargs):
        self.sensors.extend(discover_plugins('sensor', *args, **kwargs))

    # returns the elapsed milliseconds since the start of the program
    def milliseconds(self):
        return 1000*monotonic() - self.start_time

    def log(self, message):
        '''Hardware log of messages.'''
        if callable(self.hardware_log_callback):
            string = 'Interface: {0}'.format(message)
            self.hardware_log_callback(string)

    def process_lap_stats(self, node, readtime, lap_id, ms_val, cross_flag, pn_history, cross_list, upd_list):
        if not node.is_scanning:
            if cross_flag is not None and cross_flag != node.crossing_flag:  # if 'crossing' status changed
                node.crossing_flag = cross_flag
                if callable(self.node_crossing_callback):
                    cross_list.append(node)
    
            # calc lap timestamp
            if ms_val < 0 or ms_val > 9999999:
                ms_val = 0  # don't allow negative or too-large value
                node.lap_timestamp = 0
            else:
                node.lap_timestamp = readtime - (ms_val / 1000.0)
    
            # if new lap detected for node then append item to updates list
            if lap_id != node.last_lap_id:
                upd_list.append((node, lap_id, node.lap_timestamp))
    
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
                    if callable(self.new_enter_or_exit_at_callback):
                        self.new_enter_or_exit_at_callback(node, True)
    
            # check if capturing exit-at level for node
            if node.cap_exit_at_flag:
                node.cap_exit_at_total += node.current_rssi
                node.cap_exit_at_count += 1
                if self.milliseconds() >= node.cap_exit_at_millis:
                    node.exit_at_level = int(round(node.cap_exit_at_total / node.cap_exit_at_count))
                    node.cap_exit_at_flag = False
                    if callable(self.new_enter_or_exit_at_callback):
                        self.new_enter_or_exit_at_callback(node, False)

        # prune history data if race is not running (keep last 60s)
        if self.race_status is BaseHardwareInterface.RACE_STATUS_READY:
            if len(node.history_times):
                while node.history_times[0] < (monotonic() - 60):
                    node.history_values.pop(0)
                    node.history_times.pop(0)
                    if not len(node.history_times): #prevent while from destroying itself
                        break

        if pn_history and self.race_status != BaseHardwareInterface.RACE_STATUS_DONE:
            # get and process history data (except when race is over)
            pn_history.addTo(readtime, node.history_values, node.history_times, self)

    def process_crossings(self, cross_list):
        if len(cross_list) > 0:
            for node in cross_list:
                self.node_crossing_callback(node)

    def process_updates(self, upd_list):
        if len(upd_list) > 0:
            if len(upd_list) == 1:  # list contains single item
                item = upd_list[0]
                node = item[0]
                if node.last_lap_id != -1 and callable(self.pass_record_callback):
                    self.pass_record_callback(node, item[2], BaseHardwareInterface.LAP_SOURCE_REALTIME)  # (node, lap_time_absolute)
                node.last_lap_id = item[1]  # new_lap_id

            else:  # list contains multiple items; sort so processed in order by lap time
                upd_list.sort(key = lambda i: i[0].lap_timestamp)
                for item in upd_list:
                    node = item[0]
                    if node.last_lap_id != -1 and callable(self.pass_record_callback):
                        self.pass_record_callback(node, item[2], BaseHardwareInterface.LAP_SOURCE_REALTIME)  # (node, lap_time_absolute)
                    node.last_lap_id = item[1]  # new_lap_id

    #
    # External functions for setting data
    #

    def intf_simulate_lap(self, node_index, ms_val):
        node = self.nodes[node_index]
        node.lap_timestamp = monotonic() - (ms_val / 1000.0)
        self.pass_record_callback(node, node.lap_timestamp, BaseHardwareInterface.LAP_SOURCE_MANUAL)

    def set_race_status(self, race_status):
        self.race_status = race_status

    def set_calibration_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def enable_calibration_mode(self):
        pass  # dummy function; no longer supported

    def set_calibration_offset_global(self, offset):
        return offset  # dummy function; no longer supported

    def set_trigger_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def start_capture_enter_at_level(self, node_index):
        node = self.nodes[node_index]
        if node.cap_enter_at_flag is False and node.api_valid_flag:
            node.cap_enter_at_total = 0
            node.cap_enter_at_count = 0
                   # set end time for capture of RSSI level:
            node.cap_enter_at_millis = self.milliseconds() + CAP_ENTER_EXIT_AT_MILLIS
            node.cap_enter_at_flag = True
            return True
        return False

    def start_capture_exit_at_level(self, node_index):
        node = self.nodes[node_index]
        if node.cap_exit_at_flag is False and node.api_valid_flag:
            node.cap_exit_at_total = 0
            node.cap_exit_at_count = 0
                   # set end time for capture of RSSI level:
            node.cap_exit_at_millis = self.milliseconds() + CAP_ENTER_EXIT_AT_MILLIS
            node.cap_exit_at_flag = True
            return True
        return False

    def update_environmental_data(self):
        '''Updates environmental data.'''
        self.environmental_data_update_tracker += 1

        partition = (self.environmental_data_update_tracker % 2)
        for index, sensor in enumerate(self.sensors):
            if (index % 2) == partition:
                sensor.update()

    #
    # Get Json Node Data Functions
    #

    def get_settings_json(self):
        return {
            'nodes': [node.get_settings_json() for node in self.nodes],
            'calibration_threshold': self.calibration_threshold,
            'calibration_offset': self.calibration_offset,
            'trigger_threshold': self.trigger_threshold
        }

    def get_heartbeat_json(self):
        json = {
            'current_rssi': [node.current_rssi for node in self.nodes],
            'frequency': [node.frequency for node in self.nodes],
            'loop_time': [node.loop_time for node in self.nodes],
            'crossing_flag': [node.crossing_flag for node in self.nodes]
        }
        for i, node in enumerate(self.nodes):
            if node.is_scanning:
                new_freq = node.frequency + 10
                if new_freq < 5645 or new_freq > 5945:
                    new_freq = 5645
                self.set_frequency(i, new_freq)
        return json

    def get_calibration_threshold_json(self):
        return {
            'calibration_threshold': self.calibration_threshold
        }

    def get_calibration_offset_json(self):
        return {
            'calibration_offset': self.calibration_offset
        }

    def get_trigger_threshold_json(self):
        return {
            'trigger_threshold': self.trigger_threshold
        }

    def get_frequency_json(self, node_index):
        node = self.nodes[node_index]
        return {
            'node': node.index,
            'frequency': node.frequency
        }


class PeakNadirHistory:
    def addTo(self, readtime, history_values, history_times, interface):
        if self.peakRssi > 0:
            if self.nadirRssi > 0:
                # both
                if self.peakLastTime > self.nadirTime:
                    # process peak first
                    if self.peakFirstTime > self.peakLastTime:
                        history_values.append(self.peakRssi)
                        history_times.append(readtime - (self.peakFirstTime / 1000.0))
                        history_values.append(self.peakRssi)
                        history_times.append(readtime - (self.peakLastTime / 1000.0))
                    elif self.peakFirstTime == self.peakLastTime:
                        history_values.append(self.peakRssi)
                        history_times.append(readtime - (self.peakLastTime / 1000.0))
                    else:
                        interface.log('Ignoring corrupted peak history times ({0} < {1})'.format(self.peakFirstTime, self.peakLastTime))

                    history_values.append(self.nadirRssi)
                    history_times.append(readtime - (self.nadirTime / 1000.0))

                else:
                    # process nadir first
                    history_values.append(self.nadirRssi)
                    history_times.append(readtime - (self.nadirTime / 1000.0))
                    if self.peakFirstTime > self.peakLastTime:
                        history_values.append(self.peakRssi)
                        history_times.append(readtime - (self.peakFirstTime / 1000.0))
                        history_values.append(self.peakRssi)
                        history_times.append(readtime - (self.peakLastTime / 1000.0))
                    elif self.peakFirstTime == self.peakLastTime:
                        history_values.append(self.peakRssi)
                        history_times.append(readtime - (self.peakLastTime / 1000.0))
                    else:
                        interface.log('Ignoring corrupted peak history times ({0} < {1})'.format(self.peakFirstTime, self.peakLastTime))

            else:
                # peak, no nadir
                # process peak only
                if self.peakFirstTime > self.peakLastTime:
                    history_values.append(self.peakRssi)
                    history_times.append(readtime - (self.peakFirstTime / 1000.0))
                    history_values.append(self.peakRssi)
                    history_times.append(readtime - (self.peakLastTime / 1000.0))
                elif self.peakFirstTime == self.peakLastTime:
                    history_values.append(self.peakRssi)
                    history_times.append(readtime - (self.peakLastTime / 1000.0))
                else:
                    interface.log('Ignoring corrupted peak history times ({0} < {1})'.format(self.peakFirstTime, self.peakLastTime))

        elif self.nadirRssi > 0:
            # no peak, nadir
            # process nadir only
            history_values.append(self.nadirRssi)
            history_times.append(readtime - (self.nadirTime / 1000.0))
