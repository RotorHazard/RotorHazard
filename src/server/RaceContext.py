'''Primary Race management class'''

import copy
import Config
import RHRace
import RHTimeFns
import logging
from eventmanager import Evt
from led_event_manager import NoLEDManager

logger = logging.getLogger(__name__)

class RaceContext():
    def __init__(self):
        self.interface = None
        self.sensors = None
        self.cluster = None
        self.calibration = None

        self.race = None
        self.last_race = None
        self.heatautomator = None

        self.rhdata = None

        self.pagecache = None
        self.language = None

        self.events = None
        self.filters = None
        self.rhui = None

        self.led_manager = NoLEDManager()
        self.vrx_manager = None
        self.export_manager = None
        self.import_manager = None
        self.heat_generate_manager = None
        self.raceclass_rank_manager = None
        self.race_points_manager = None
        self.plugin_manager = None

        self.serverconfig = Config.Config(self)
        self.serverstate = ServerState(self)

    def branch_race_obj(self):
        self.last_race = RHRace.RHRace(self)

        self.last_race.num_nodes = self.race.num_nodes
        self.last_race.current_heat = self.race.current_heat
        self.last_race.node_pilots = self.race.node_pilots
        self.last_race.node_teams = self.race.node_teams
        self.last_race.format = self.race.format
        self.last_race.profile = self.race.profile
        # sequence
        self.last_race.scheduled = self.race.scheduled
        self.last_race.scheduled_time = self.race.scheduled_time
        self.last_race.start_token = self.race.start_token
        # status
        self.last_race.race_status = self.race.race_status
        self.last_race.timer_running = self.race.timer_running
        self.last_race.stage_time_monotonic = self.race.stage_time_monotonic
        self.last_race.start_time = self.race.start_time
        self.last_race.start_time_monotonic = self.race.start_time_monotonic
        self.last_race.start_time_epoch_ms = self.race.start_time_epoch_ms
        self.last_race.node_laps = self.race.node_laps
        self.last_race.node_has_finished = self.race.node_has_finished
        self.last_race.any_races_started = self.race.any_races_started
        # concluded
        self.last_race.end_time = self.race.end_time
        # leaderboard/cache
        self.last_race.results = self.race.results
        self.last_race.cacheStatus = self.race.cacheStatus
        self.last_race.status_message = self.race.status_message
        self.last_race.team_results = self.race.team_results
        self.last_race.team_cacheStatus = self.race.team_cacheStatus
        self.last_race.win_status = self.race.win_status

        self.last_race.db_id = self.race.db_id

class ServerState:
    def __init__(self, racecontext):
        self._racecontext = racecontext

    # PLUGIN STATUS
    plugins = None

    @property
    def info_dict(self):
        return {
            'release_version': self.release_version,
            'server_api': self.server_api_version,
            'json_api': self.json_api_version,
            'prog_start_epoch': self._program_start_epoch_formatted,
            'prog_start_time': self._program_start_time_formatted,
            'node_api_match': self.node_api_match,
            'node_api_lowest': self.node_api_lowest,
            'node_api_best': self.node_api_best,
            'node_api_levels': self.node_api_levels,
            'node_version_match': self.node_version_match,
            'node_fw_versions': self.node_fw_versions,
        }

    @property
    def template_info_dict(self):
        info = self.info_dict
        info['about_html'] = self.info_html
        return info

    # BASIC INFO

    release_version = None
    server_api_version = None
    json_api_version = None
    node_api_match = None
    node_api_lowest = 0
    node_api_best = None
    node_api_levels = [None]
    node_version_match = None
    node_fw_versions = [None]

    _info_html = None

    @property
    def info_html(self):
        if self._info_html is None:
            self.build_html()
        return self._info_html

    def build_info(self):
        # Node API levels
        node_api_level = 0
        node_api_match = True
        node_api_lowest = 0
        node_api_levels = [None]

        info_node = self._racecontext.interface.get_info_node_obj()
        if info_node:
            if info_node.api_level:
                node_api_level = info_node.api_level
                node_api_lowest = node_api_level
                if len(self._racecontext.interface.nodes):
                    node_api_levels = []
                    for node in self._racecontext.interface.nodes:
                        node_api_levels.append(node.api_level)
                        if node.api_level != node_api_level:
                            node_api_match = False
                        if node.api_level < node_api_lowest:
                            node_api_lowest = node.api_level
                    # if multi-node and all api levels same then only include one entry
                    if node_api_match and self._racecontext.interface.nodes[0].multi_node_index >= 0:
                        node_api_levels = node_api_levels[0:1]
                else:
                    node_api_levels = [node_api_level]

        self.node_api_match = node_api_match
        self.node_api_lowest = node_api_lowest
        self.node_api_levels = node_api_levels

        # Node firmware versions
        node_fw_version = None
        node_version_match = True
        node_fw_versions = [None]
        if info_node:
            if info_node.firmware_version_str:
                node_fw_version = info_node.firmware_version_str
                if len(self._racecontext.interface.nodes):
                    node_fw_versions = []
                    for node in self._racecontext.interface.nodes:
                        node_fw_versions.append(\
                                node.firmware_version_str if node.firmware_version_str else "0")
                        if node.firmware_version_str != node_fw_version:
                            node_version_match = False
                    # if multi-node and all versions same then only include one entry
                    if node_version_match and self._racecontext.interface.nodes[0].multi_node_index >= 0:
                        node_fw_versions = node_fw_versions[0:1]
                else:
                    node_fw_versions = [node_fw_version]

        self.node_version_match = node_version_match
        self.node_fw_versions = node_fw_versions
        self.build_html()

    def build_html(self):
        html_output = "<ul>"
        html_output += "<li>" + self._racecontext.language.__("Version") + ": " + str(self.release_version) + "</li>"

        html_output += "<li>" + self._racecontext.language.__("Server API") + ": " + str(self.server_api_version) + "</li>"

        # Node API
        html_output += "<li>" + self._racecontext.language.__("Node API") + ": "
        if self.node_api_levels[0]:
            if self.node_api_match:
                html_output += str(self.node_api_levels[0])
            else:
                html_output += "[ "
                for idx, level in enumerate(self.node_api_levels):
                    html_output += str(idx+1) + ":" + str(level) + " "
                html_output += "]"
        else:
            html_output += "None (Delta5)"
        html_output += "</li>"

        # Node Version
        if self.node_fw_versions[0]:
            html_output += "<li>" + self._racecontext.language.__("Node Version") + ": "
            if self.node_version_match:
                html_output += str(self.node_fw_versions[0])
            else:
                html_output += "[ "
                for idx, ver in enumerate(self.node_fw_versions):
                    html_output += str(idx+1) + ":" + str(ver) + " "
                html_output += "]"
            html_output += "</li>"

        if self.node_api_match is False or self.node_api_lowest < self.node_api_best:
            # Show Recommended API notice
            html_output += "<li><strong>" + self._racecontext.language.__("Node Update Available") + ": " + str(self.node_api_best) + "</strong></li>"

        self._info_html = html_output

    # SERVER TIME

    # epoch time of server launch
    _program_start_epoch_time = None
    # monotonic time of server launch
    _program_start_mtonic = None
    # offset for converting 'monotonic' time to epoch milliseconds since 1970-01-01
    _mtonic_to_epoch_millis_offset = None
    _program_start_epoch_formatted = None
    _program_start_time_formatted = None
    # token used for tracking server restart from frontend
    _server_instance_token = None

    @property
    def program_start_epoch_time(self):
        return self._program_start_epoch_time

    @program_start_epoch_time.setter
    def program_start_epoch_time(self, value):
        self._program_start_epoch_formatted = "{0:.0f}".format(value)
        self._program_start_time_formatted = RHTimeFns.epochMsToFormattedStr(value)
        self._program_start_epoch_time = value

    @property
    def program_start_mtonic(self):
        return self._program_start_mtonic

    @program_start_mtonic.setter
    def program_start_mtonic(self, value):
        self._program_start_mtonic = value

    @property
    def server_instance_token(self):
        return self._server_instance_token

    @server_instance_token.setter
    def server_instance_token(self, value):
        self._server_instance_token = value

    @property
    def mtonic_to_epoch_millis_offset(self):
        return self._mtonic_to_epoch_millis_offset

    @mtonic_to_epoch_millis_offset.setter
    def mtonic_to_epoch_millis_offset(self, value):
        self._mtonic_to_epoch_millis_offset = value

    @property
    def program_start_epoch_formatted(self):
        return self._program_start_epoch_formatted

    @property
    def program_start_time_formatted(self):
        return self._program_start_time_formatted

    # convert 'monotonic' time to epoch milliseconds since 1970-01-01
    def monotonic_to_epoch_millis(self, secs):
        return 1000.0*secs + self.mtonic_to_epoch_millis_offset

    def epoch_millis_to_monotonic(self, secs):
        return (secs - self.mtonic_to_epoch_millis_offset)/1000.0

    # SERVER GLOBALS

    # race format used in secondary mode (must be initialized after database)
    secondary_race_format = None

    _seat_color_defaults = [
        "#0022ff",  # Blue
        "#ff5500",  # Orange
        "#00ff22",  # Green
        "#ff0055",  # Magenta
        "#ddff00",  # Yellow
        "#7700ff",  # Purple
        "#00ffdd",  # Teal
        "#aaaaaa",  # White
    ]

    @property
    def seat_color_defaults(self):
        return copy.copy(self._seat_color_defaults)

    # enable processing of Evt.ALL events when Evt.HEARTBEAT is triggered
    enable_heartbeat_event = False

    # flag if restart is needed (after plugin install, etc.)
    restart_required = False

    def set_restart_required(self):
        if not self.restart_required:
            self.restart_required = True
            self._racecontext.events.trigger(Evt.RESTART_REQUIRED, {})
            self._racecontext.rhui.emit_restart_required()
