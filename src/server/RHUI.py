#
# RHUI Helper
# Provides abstraction for user interface
#
from typing import List, Any  # @UnusedImport
from dataclasses import dataclass, asdict  # @UnresolvedImport
from enum import Enum
from flask import request
from flask_socketio import emit
from eventmanager import Evt
import json
import subprocess
import re
from collections import OrderedDict
import gevent
import RHUtils
from RHUtils import catchLogExceptionsWrapper
from Database import ProgramMethod, RoundType
from RHRace import RacingMode
from filtermanager import Flt
import logging
logger = logging.getLogger(__name__)

from FlaskAppObj import APP
APP.app_context().push()

class UIFieldType(Enum):
    TEXT = "text"
    BASIC_INT = "basic_int"
    NUMBER = "number"
    RANGE = "range"
    SELECT = "select"
    CHECKBOX = "checkbox"
    PASSWORD = "password"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    EMAIL = "email"
    TEL = "tel"
    URL = "url"

@dataclass
class UIFieldSelectOption():
    value: str
    label: str

@dataclass
class UIField():
    name: str
    label: str
    field_type: str = UIFieldType.TEXT
    value: Any = None
    desc: str = None
    placeholder: str = None
    options: List[UIFieldSelectOption] = None
    order: int = 0 # not implemented
    private: bool = False
    html_attributes: dict = None

    def frontend_repr(self):
        return {
            'name': self.name,
            'label': self.label,
            'field_type': self.field_type.value,
            'value': self.value,
            'desc' : self.desc,
            'placeholder': self.placeholder,
            'options': [asdict(option) for option in self.options] if self.options else None,
            'order': self.order,
            'html_attributes': self.html_attributes
        }

@dataclass
class UIPanel():
    name: str
    label: str
    page: str
    order: int = 0
    open: bool = False

@dataclass
class GeneralSetting():
    name: str
    field: UIField
    panel: str = None
    order: int = 0

@dataclass
class QuickButton():
    panel: str
    name: str
    label: str
    fn: callable
    args: dict

@dataclass
class Markdown():
    panel: str
    name: str
    desc: str

class RHUI():
    # Language placeholder (Overwritten after module init)
    def __(self, *args):
        return args

    def __init__(self, APP, SOCKET_IO, RaceContext, Events):
        self._app = APP
        self._socket = SOCKET_IO
        self._racecontext = RaceContext
        self._events = Events
        self._filters = RaceContext.filters

        self._pilot_attributes = []
        self._heat_attributes = []
        self._raceclass_attributes = []
        self._savedrace_attributes = []
        self._raceformat_attributes = []
        self._ui_panels = []
        self._general_settings = []
        self._quickbuttons = []
        self._markdowns = []

    # Pilot Attributes
    def register_pilot_attribute(self, field:UIField):
        for idx, attribute in enumerate(self._pilot_attributes):
            if attribute.name == field.name:
                self._pilot_attributes[idx] = field
                logger.debug(F'Redefining pilot attribute "{field.name}"')
                break
        else:
            self._pilot_attributes.append(field)
        return self._pilot_attributes

    @property
    def pilot_attributes(self):
        return self._pilot_attributes

    # Heat Attributes
    def register_heat_attribute(self, field:UIField):
        for idx, attribute in enumerate(self._heat_attributes):
            if attribute.name == field.name:
                self._heat_attributes[idx] = field
                logger.debug(F'Redefining heat attribute "{field.name}"')
                break
        else:
            self._heat_attributes.append(field)
        return self._heat_attributes

    @property
    def heat_attributes(self):
        return self._heat_attributes

    # Race Class Attributes
    def register_raceclass_attribute(self, field:UIField):
        for idx, attribute in enumerate(self._raceclass_attributes):
            if attribute.name == field.name:
                self._raceclass_attributes[idx] = field
                logger.debug(F'Redefining raceclass attribute "{field.name}"')
                break
        else:
            self._raceclass_attributes.append(field)
        return self._raceclass_attributes

    @property
    def raceclass_attributes(self):
        return self._raceclass_attributes

    # Race Attributes
    def register_savedrace_attribute(self, field:UIField):
        for idx, attribute in enumerate(self._savedrace_attributes):
            if attribute.name == field.name:
                self._savedrace_attributes[idx] = field
                logger.debug(F'Redefining savedrace attribute "{field.name}"')
                break
        else:
            self._savedrace_attributes.append(field)
        return self._savedrace_attributes

    @property
    def savedrace_attributes(self):
        return self._savedrace_attributes

    # Race Format Attributes
    def register_raceformat_attribute(self, field:UIField):
        for idx, attribute in enumerate(self._raceformat_attributes):
            if attribute.name == field.name:
                self._raceformat_attributes[idx] = field
                logger.debug(F'Redefining raceformat attribute "{field.name}"')
                break
        else:
            self._raceformat_attributes.append(field)
        return self._raceformat_attributes

    @property
    def raceformat_attributes(self):
        return self._raceformat_attributes

    # UI Panels
    def register_ui_panel(self, name, label, page, order=0, open = False,):
        for idx, panel in enumerate(self._ui_panels):
            if panel.name == name:
                self._ui_panels[idx] = UIPanel(name, label, page, order, open)
                logger.debug(F'Redefining panel "{name}"')
                break
        else:
            self._ui_panels.append(UIPanel(name, label, page, order, open))
        return self.ui_panels

    @property
    def ui_panels(self):
        return self._ui_panels

    # General Settings
    def register_general_setting(self, field:UIField, panel=None, order=0):
        for idx, setting in enumerate(self._general_settings):
            if setting.name == field.name:
                self._general_settings[idx] = GeneralSetting(field.name, field, panel, order)
                logger.debug(F'Redefining setting "{field.name}"')
                break
        else:
            self._general_settings.append(GeneralSetting(field.name, field, panel, order))
        return self._general_settings

    @property
    def general_settings(self):
        return self._general_settings

    # button
    def register_quickbutton(self, panel, name, label, fn, args=None):
        for idx, button in enumerate(self._quickbuttons):
            if button.name == name:
                self._quickbuttons[idx] = QuickButton(panel, name, label, fn, args)
                logger.debug(F'Redefining quickbutton "{name}"')
                break
        else:
            self._quickbuttons.append(QuickButton(panel, name, label, fn, args))
        return self._quickbuttons

    def get_panel_settings(self, name):
        payload = []
        for setting in self.general_settings:
            if setting.panel == name:
                payload.append(setting)

        return payload

    def get_panel_quickbuttons(self, name):
        payload = []
        for btn in self._quickbuttons:
            if btn.panel == name:
                payload.append(btn)

        return payload

    def dispatch_quickbuttons(self, args):
        if 'namespace' in args and args['namespace'] == 'quickbutton':
            for btn in self._quickbuttons:
                if btn.name == args['id']:
                    btn.fn(btn.args)
                    return

    # Markdown
    def register_markdown(self, panel, name, desc):
        for idx, markdown in enumerate(self._markdowns):
            if markdown.name == name:
                self._markdowns[idx] = Markdown(panel, name, desc)
                logger.debug(F'Redefining markdown "{name}"')
                break
        else:
            self._markdowns.append(Markdown(panel, name, desc))
        return self._markdowns

    def get_panel_markdowns(self, name):
        payload = []
        for md in self.markdowns:
            if md.panel == name:
                payload.append(md)

        return payload

    @property
    def markdowns(self):
        return self._markdowns

    # Blueprints
    def add_blueprint(self, blueprint):
        self._app.register_blueprint(blueprint)

    # Socket generics
    def socket_listen(self, message, handler):
        self._socket.on_event(message, handler)

    def socket_send(self, message, data):
        emit(message, data)

    def socket_broadcast(self, message, data):
        self._socket.emit(message, data)

    # General Emits
    def emit_frontend_load(self, **params):
        '''Emits reload command.'''
        if ('nobroadcast' in params):
            emit('load_all')
        else:
            self._socket.emit('load_all')

    def emit_ui(self, page, **params):
        '''Emits UI objects'''

        emit_payload = {
            'page': page,
            'panels': []
        }

        for panel in self.ui_panels:
            if panel.page == page:
                settings = []
                for setting in self.get_panel_settings(panel.name):
                    field = setting.field.frontend_repr()

                    db_val = self._racecontext.rhdata.get_option(setting.name)
                    if db_val is not None:
                        field['value'] = db_val != '0' if setting.field.field_type is UIFieldType.CHECKBOX else db_val

                    settings.append(field)

                buttons = []
                for button in self.get_panel_quickbuttons(panel.name):
                    buttons.append({
                        'name': button.name,
                        'label': button.label,
                    })

                markdowns = []
                for md in self.get_panel_markdowns(panel.name):
                    markdowns.append({
                        'name': md.name,
                        'desc': md.desc,
                    })

                emit_payload['panels'].append({
                    'panel': {
                        'name': panel.name,
                        'label': panel.label,
                        'order': panel.order,
                        'open': panel.open,
                    },
                    'settings': settings,
                    'quickbuttons': buttons,
                    'markdowns': markdowns
                })

        emit_payload = self._filters.run_filters(Flt.EMIT_UI, emit_payload)

        if ('nobroadcast' in params):
            emit('ui', emit_payload)
        else:
            self._socket.emit('ui', emit_payload)

    def emit_priority_message(self, message, interrupt=False, caller=False, admin_only=False, **params):
        ''' Emits message to all clients '''
        if message and re.search(r"[0-\udfff]", message):  # don't emit if msg is only whitespace and punctuation
            logger.debug("Emitting {}: {}".format(("alert" if interrupt else "message"), message))
            emit_payload = {
                'message': message,
                'interrupt': interrupt
            }
            if admin_only:
                emit_payload['admin_only'] = True
            if ('nobroadcast' in params):
                emit('priority_message', emit_payload)
            else:
                if interrupt:
                    self._events.trigger(Evt.MESSAGE_INTERRUPT, {
                        'message': message,
                        'interrupt': interrupt,
                        'caller': caller
                        })
                else:
                    self._events.trigger(Evt.MESSAGE_STANDARD, {
                        'message': message,
                        'interrupt': interrupt,
                        'caller': caller
                        })

                self._socket.emit('priority_message', emit_payload)

    def emit_plugin_list(self, **params):
        plugins = self._racecontext.serverstate.plugins
        manager_local_data = self._racecontext.plugin_manager.get_display_data()

        plugin_data = []
        for plugin in plugins:
            if not plugin.is_bundled:
                plugin_info = {
                    'name': None,
                    'author': None,
                    'author_uri': None,
                    'description': None,
                    'documentation_uri': None,
                    'info_uri': None,
                    'license': None,
                    'license_uri': None,
                    'version': None,
                    'required_rhapi_version': None,
                    'update_uri': None,
                    'text_domain': None,
                    'update_status': None,
                }
                if plugin.meta:
                    for key, value in plugin.meta.items():
                        if key in plugin_info:
                            plugin_info[key] = value
                else:
                    plugin_info['name'] = plugin.name

                plugin_info['id'] = plugin.name
                plugin_info['enabled'] = plugin.enabled
                plugin_info['loaded'] = plugin.loaded
                plugin_info['load_issue'] = plugin.load_issue

                if manager_local_data and plugin.name in manager_local_data:
                    plugin_info['update_status'] = manager_local_data[plugin.name]['update_status']

                plugin_data.append(plugin_info)

        emit_payload = {
            'plugins': plugin_data
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_PLUGIN_LIST, emit_payload)

        if ('nobroadcast' in params):
            emit('plugin_list', emit_payload)
        else:
            self._socket.emit('plugin_list', emit_payload)

    def emit_plugin_repo(self, **params):
        plugin_data = self._racecontext.plugin_manager.get_display_data()
        category_data = self._racecontext.plugin_manager.get_remote_categories()

        emit_payload = {
            'remote_categories': category_data,
            'remote_data': plugin_data
        }

        if ('nobroadcast' in params):
            emit('plugin_repo', emit_payload)
        else:
            self._socket.emit('plugin_repo', emit_payload)

    def emit_option_update(self, options, **params):
        option_vals = {}
        if isinstance(options, str):
            option_vals[options] = self._racecontext.rhdata.get_option(options)

        if isinstance(options, list):
            for opt in options:
                option_vals[opt] = self._racecontext.rhdata.get_option(opt)

        emit_payload = {
            'options': option_vals
        }

        if ('nobroadcast' in params):
            emit('option_update', emit_payload)
        else:
            self._socket.emit('option_update', emit_payload)

    def emit_config_update(self, settings, **params):
        config_vals = {}
        for section, items in settings.items():
            if section == 'SENSORS':
                config_vals['SENSORS'] = self._racecontext.serverconfig.get_section('SENSORS')
            else:
                for item in items:
                    if section not in config_vals:
                        config_vals[section] = {}

                    config_vals[section][item] = self._racecontext.serverconfig.get_item(section, item)

        emit_payload = {
            'config': config_vals
        }

        if ('nobroadcast' in params):
            emit('config_update', emit_payload)
        else:
            self._socket.emit('config_update', emit_payload)

    def emit_heat_plan_result(self, new_heat_id, calc_result):
        heat = self._racecontext.rhdata.get_heat(new_heat_id)
        heatNodes = []

        heatNode_objs = self._racecontext.rhdata.get_heatNodes_by_heat(heat.id)
        heatNode_objs.sort(key=lambda x: x.id)

        profile_freqs = json.loads(self._racecontext.race.profile.frequencies)

        for heatNode in heatNode_objs:
            heatNode_data = {
                'node_index': heatNode.node_index,
                'pilot_id': heatNode.pilot_id,
                'callsign': None,
                'method': heatNode.method,
                'seed_rank': heatNode.seed_rank,
                'seed_id': heatNode.seed_id
                }
            if heatNode.pilot_id:
                pilot = self._racecontext.rhdata.get_pilot(heatNode.pilot_id)
                if pilot:
                    heatNode_data['callsign'] = pilot.callsign
                    if pilot.used_frequencies and heatNode.node_index is not None:
                        used_freqs = json.loads(pilot.used_frequencies)
                        heatNode_data['frequency_change'] = (used_freqs[-1]['f'] != profile_freqs["f"][heatNode.node_index])
                    else:
                        heatNode_data['frequency_change'] = True

            heatNodes.append(heatNode_data)

        emit_payload = {
            'heat': new_heat_id,
            'displayname': heat.display_name,
            'slots': heatNodes,
            'calc_result': calc_result
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_HEAT_PLAN, emit_payload)

        self._socket.emit('heat_plan_result', emit_payload)

    def emit_race_stage(self, payload):
        self._socket.emit('stage_ready', payload)

    def emit_race_stop(self):
        self._socket.emit('stop_timer')

    def emit_clear_priority_messages(self):
        self._socket.emit('clear_priority_messages')

    def emit_race_schedule(self):
        self._socket.emit('race_scheduled', {
            'scheduled': self._racecontext.race.scheduled,
            'scheduled_at': self._racecontext.race.scheduled_time
            })

    def emit_race_status(self, **params):
        '''Emits race status.'''
        race_format = self._racecontext.race.format
        heat_id = self._racecontext.race.current_heat
        if heat_id:
            heat = self._racecontext.rhdata.get_heat(heat_id)
            class_id = heat.class_id
            race_class = self._racecontext.rhdata.get_raceClass(class_id)
        else:
            class_id = None

        emit_payload = {
                'race_status': self._racecontext.race.race_status,
                'race_format_id': self._racecontext.race.format.id if hasattr(self._racecontext.race.format, 'id') else None,
                'race_heat_id': heat_id,
                'race_class_id': class_id,
                'unlimited_time': self._racecontext.race.unlimited_time,
                'race_time_sec': self._racecontext.race.race_time_sec,
                'staging_tones': 0,
                'hide_stage_timer': race_format.start_delay_min_ms != race_format.start_delay_max_ms,
                'pi_starts_at_s': self._racecontext.race.start_time_monotonic,
                'pi_staging_at_s': self._racecontext.race.stage_time_monotonic,
                'show_init_time_flag': self._racecontext.race.show_init_time_flag
            }
        if class_id and race_class.round_type == RoundType.GROUPED:
            emit_payload['next_round'] = heat.group_id + 1
        else:
            emit_payload['next_round'] = self._racecontext.rhdata.get_round_num_for_heat(heat_id)

        if ('nobroadcast' in params):
            emit('race_status', emit_payload)
        else:
            self._socket.emit('race_status', emit_payload)

    def emit_frequency_data(self, **params):
        '''Emits node data.'''
        profile_freqs = json.loads(self._racecontext.race.profile.frequencies)

        fdata = []
        for idx in range(self._racecontext.race.num_nodes):
            fdata.append({
                    'band': profile_freqs["b"][idx],
                    'channel': profile_freqs["c"][idx],
                    'frequency': profile_freqs["f"][idx]
                })

        emit_payload = {
                'fdata': fdata
            }

        if ('nobroadcast' in params):
            emit('frequency_data', emit_payload)
        else:
            self._socket.emit('frequency_data', emit_payload)

            # send changes to LiveTime
            for n in range(self._racecontext.race.num_nodes):
                # if session.get('LiveTime', False):
                self._socket.emit('frequency_set', {
                    'node': n,
                    'frequency': profile_freqs["f"][n]
                })

    def emit_node_data(self, **params):
        '''Emits node data.'''
        emit_payload = {
                'node_peak_rssi': [node.node_peak_rssi for node in self._racecontext.interface.nodes],
                'node_nadir_rssi': [node.node_nadir_rssi for node in self._racecontext.interface.nodes],
                'pass_peak_rssi': [node.pass_peak_rssi for node in self._racecontext.interface.nodes],
                'pass_nadir_rssi': [node.pass_nadir_rssi for node in self._racecontext.interface.nodes],
                'debug_pass_count': [node.debug_pass_count for node in self._racecontext.interface.nodes]
            }
        if ('nobroadcast' in params):
            emit('node_data', emit_payload)
        else:
            self._socket.emit('node_data', emit_payload)

    def emit_environmental_data(self, **params):
        '''Emits environmental data.'''
        emit_payload = []
        for sensor in self._racecontext.sensors:
            emit_payload.append({sensor.name: sensor.getReadings()})

        emit_payload = self._filters.run_filters(Flt.EMIT_SENSOR_DATA, emit_payload)

        if ('nobroadcast' in params):
            emit('environmental_data', emit_payload)
        else:
            self._socket.emit('environmental_data', emit_payload)

    def emit_enter_and_exit_at_levels(self, **params):
        '''Emits enter-at and exit-at levels for nodes.'''
        profile = self._racecontext.race.profile
        profile_enter_ats = json.loads(profile.enter_ats)
        profile_exit_ats = json.loads(profile.exit_ats)

        emit_payload = {
            'enter_at_levels': profile_enter_ats["v"][:self._racecontext.race.num_nodes],
            'exit_at_levels': profile_exit_ats["v"][:self._racecontext.race.num_nodes]
        }
        if ('nobroadcast' in params):
            emit('enter_and_exit_at_levels', emit_payload)
        else:
            self._socket.emit('enter_and_exit_at_levels', emit_payload)

    def emit_cluster_status(self, **params):
        '''Emits cluster status information.'''
        if self._racecontext.cluster:
            if ('nobroadcast' in params):
                emit('cluster_status', self._racecontext.cluster.getClusterStatusInfo())
            else:
                self._socket.emit('cluster_status', self._racecontext.cluster.getClusterStatusInfo())

    def emit_start_thresh_lower_amount(self, **params):
        '''Emits current start_thresh_lower_amount.'''
        emit_payload = {
            'start_thresh_lower_amount': self._racecontext.serverconfig.get_item_int('TIMING', 'startThreshLowerAmount'),
        }
        if ('nobroadcast' in params):
            emit('start_thresh_lower_amount', emit_payload)
        else:
            self._socket.emit('start_thresh_lower_amount', emit_payload)

    def emit_start_thresh_lower_duration(self, **params):
        '''Emits current start_thresh_lower_duration.'''
        emit_payload = {
            'start_thresh_lower_duration': self._racecontext.serverconfig.get_item_int('TIMING', 'startThreshLowerDuration'),
        }
        if ('nobroadcast' in params):
            emit('start_thresh_lower_duration', emit_payload)
        else:
            self._socket.emit('start_thresh_lower_duration', emit_payload)

    def emit_node_tuning(self, **params):
        '''Emits node tuning values.'''
        tune_val = self._racecontext.race.profile
        emit_payload = {
            'profile_ids': [profile.id for profile in self._racecontext.rhdata.get_profiles()],
            'profile_names': [profile.name for profile in self._racecontext.rhdata.get_profiles()],
            'current_profile': self._racecontext.rhdata.get_optionInt('currentProfile'),
            'profile_name': tune_val.name,
            'profile_description': tune_val.description
        }
        if ('nobroadcast' in params):
            emit('node_tuning', emit_payload)
        else:
            self._socket.emit('node_tuning', emit_payload)

    def emit_language(self, **params):
        '''Emits race status.'''
        emit_payload = {
                'language': self._racecontext.serverconfig.get_item('UI', 'currentLanguage'),
                'languages': self._racecontext.language.getLanguages()
            }
        if ('nobroadcast' in params):
            emit('language', emit_payload)
        else:
            self._socket.emit('language', emit_payload)

    def emit_all_languages(self, **params):
        '''Emits full language dictionary.'''
        emit_payload = {
                'languages': self._racecontext.language.getAllLanguages()
            }
        if ('nobroadcast' in params):
            emit('all_languages', emit_payload)
        else:
            self._socket.emit('all_languages', emit_payload)

    def emit_action_setup(self, EventActionsObj, **params):
        '''Emits events and effects for actions.'''
        emit_payload = {
            'enabled': False
        }

        if EventActionsObj:
            effects = EventActionsObj.getRegisteredEffects()

            if effects:
                effect_list = {}
                for effect in effects:
                    effect_list[effect] = {
                        'name': self.__(effects[effect].label),
                        'fields': [field.frontend_repr() for field in effects[effect].fields] if effects[effect].fields else None
                    }

                events_list = {
                    Evt.RACE_STAGE: 'Race Stage',
                    Evt.RACE_START: 'Race Start',
                    Evt.RACE_FINISH: 'Race Finish',
                    Evt.RACE_STOP: 'Race Stop',
                    Evt.RACE_WIN: 'Race Win',
                    Evt.RACE_INITIAL_PASS: 'Race Initial Pass',
                    Evt.RACE_PILOT_LEADING: 'Pilot Leading',
                    Evt.RACE_PILOT_DONE: 'Pilot Done',
                    Evt.HEAT_SET: 'Heat Change',
                    Evt.RACE_SCHEDULE: 'Race Schedule',
                    Evt.RACE_SCHEDULE_CANCEL: 'Cancel Scheduled Race',
                    Evt.LAPS_SAVE: 'Save Laps',
                    Evt.LAPS_DISCARD: 'Discard Laps',
                    Evt.ROUNDS_COMPLETE: 'Rounds Complete'
                }

                # if event names for any configured events not in list then add them
                for item in EventActionsObj.getEventActionsList():
                    event_name = item.get('event')
                    if event_name and not event_name in events_list:
                        events_list[event_name] = event_name

                emit_payload = {
                    'enabled': True,
                    'events': events_list,
                    'effects': effect_list,
                }

        if ('nobroadcast' in params):
            emit('action_setup', emit_payload)
        else:
            self._socket.emit('action_setup', emit_payload)

    def emit_event_actions(self, **params):
        '''Emits event actions.'''
        emit_payload = {
            'actions': self._racecontext.serverconfig.get_item('USER', 'actions'),
        }
        if ('nobroadcast' in params):
            emit('event_actions', emit_payload)
        else:
            self._socket.emit('event_actions', emit_payload)

    def emit_min_lap(self, **params):
        '''Emits current minimum lap.'''
        emit_payload = {
            'min_lap': self._racecontext.rhdata.get_optionInt('MinLapSec'),
            'min_lap_behavior': self._racecontext.serverconfig.get_item_int('TIMING', 'MinLapBehavior')
        }
        if ('nobroadcast' in params):
            emit('min_lap', emit_payload)
        else:
            self._socket.emit('min_lap', emit_payload)

    def emit_current_laps(self, **params):
        '''Emits current laps.'''
        emit_payload = {
            'current': {}
        }
        emit_payload['current'] = self._racecontext.race.get_lap_results()

        if self._racecontext.last_race is not None:
            emit_payload['last_race'] = self._racecontext.last_race.get_lap_results()

        if ('nobroadcast' in params):
            emit('current_laps', emit_payload)
        else:
            self._socket.emit('current_laps', emit_payload)

    def emit_race_list(self, **params):
        '''Emits race listing'''
        profile_freqs = json.loads(self._racecontext.race.profile.frequencies)
        heats = {}
        for heat in self._racecontext.rhdata.get_heats():
            if self._racecontext.rhdata.savedRaceMetas_has_heat(heat.id):
                rounds = {}
                for race in self._racecontext.rhdata.get_savedRaceMetas_by_heat(heat.id):
                    pilotraces = []
                    for pilotrace in self._racecontext.rhdata.get_savedPilotRaces_by_savedRaceMeta(race.id):
                        pilot_data = self._racecontext.rhdata.get_pilot(pilotrace.pilot_id)
                        if pilot_data:
                            nodepilot = pilot_data.callsign
                        else:
                            nodepilot = None

                        pilotraces.append({
                            'pilotrace_id': pilotrace.id,
                            'callsign': nodepilot,
                            'pilot_id': pilotrace.pilot_id,
                            'node_index': pilotrace.node_index,
                            'pilot_freq': self.get_pilot_freq_info(profile_freqs, pilotrace.frequency, \
                                                                   pilotrace.node_index)
                        })
                    rounds[race.round_id] = {
                        'race_id': race.id,
                        'format_id': race.format_id,
                        'start_time': race.start_time,
                        'start_time_formatted': race.start_time_formatted,
                        'pilotraces': pilotraces
                    }
                heats[heat.id] = {
                    'heat_id': heat.id,
                    'class_id': heat.class_id,
                    'displayname': heat.display_name,
                    'rounds': rounds,
                }
                if heat.class_id:
                    race_class = self._racecontext.rhdata.get_raceClass(heat.class_id)
                    heats[heat.id]['round_type'] = race_class.round_type

        emit_payload = {
            'heats': heats,
            # 'heats_by_class': heats_by_class,
            # 'classes': current_classes,
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_RACE_LIST, emit_payload)

        if ('nobroadcast' in params):
            emit('race_list', emit_payload)
        else:
            self._socket.emit('race_list', emit_payload)

    def emit_result_data(self, **params):
        ''' kick off non-blocking thread to generate data'''
        if request:
            gevent.spawn(self.emit_result_data_thread, params, request.sid)
        else:
            gevent.spawn(self.emit_result_data_thread, params)

    @catchLogExceptionsWrapper
    def emit_result_data_thread(self, params, sid=None):
        with self._app.test_request_context():

            emit_payload = self._racecontext.pagecache.get_cache()

            if 'nobroadcast' in params and sid != None:
                emit('result_data', emit_payload, namespace='/', room=sid)
            else:
                self._socket.emit('result_data', emit_payload, namespace='/')

    def emit_current_leaderboard(self, **params):
        '''Emits leaderboard.'''

        emit_payload = {
            'current': {}
        }

        # current
        if self._racecontext.race.current_heat is RHUtils.HEAT_ID_NONE:
            emit_payload['current']['displayname'] = self.__("Practice")
        else:
            heat = self._racecontext.rhdata.get_heat(self._racecontext.race.current_heat)
            if heat:
                emit_payload['current']['displayname'] = heat.display_name

        emit_payload['current']['heat'] = self._racecontext.race.current_heat
        emit_payload['current']['round'] = self._racecontext.rhdata.get_round_num_for_heat( \
                                                       self._racecontext.race.current_heat)
        emit_payload['current']['status_msg'] = self._racecontext.race.status_message

        emit_payload['current']['leaderboard'] = self._racecontext.race.get_results()

        if self._racecontext.race.format.team_racing_mode == RacingMode.TEAM_ENABLED:
            emit_payload['current']['team_leaderboard'] = self._racecontext.race.get_team_results()
        elif self._racecontext.race.format.team_racing_mode == RacingMode.COOP_ENABLED:
            emit_payload['current']['team_leaderboard'] = self._racecontext.race.get_coop_results()

        # cache
        if self._racecontext.last_race:
            emit_payload['last_race'] = {}

            if self._racecontext.last_race.current_heat is RHUtils.HEAT_ID_NONE:
                emit_payload['last_race']['displayname'] = self.__("Practice")
            else:
                heat = self._racecontext.rhdata.get_heat(self._racecontext.last_race.current_heat)
                if heat:
                    emit_payload['last_race']['displayname'] = self._racecontext.rhdata.get_heat(self._racecontext.last_race.current_heat).display_name

            emit_payload['last_race']['heat'] = self._racecontext.last_race.current_heat
            emit_payload['last_race']['round'] = self._racecontext.rhdata.get_max_round( \
                                                        self._racecontext.last_race.current_heat)
            emit_payload['last_race']['status_msg'] = self._racecontext.last_race.status_message

            emit_payload['last_race']['leaderboard'] = self._racecontext.last_race.get_results()

            if self._racecontext.last_race.format.team_racing_mode == RacingMode.TEAM_ENABLED:
                emit_payload['last_race']['team_leaderboard'] = self._racecontext.last_race.get_team_results()
            elif self._racecontext.last_race.format.team_racing_mode == RacingMode.COOP_ENABLED:
                emit_payload['last_race']['team_leaderboard'] = self._racecontext.last_race.get_coop_results()

        if ('nobroadcast' in params):
            emit('leaderboard', emit_payload)
        else:
            self._socket.emit('leaderboard', emit_payload)

    def emit_expanded_heat(self, heat_id, **params):
        '''Emits abbreviated heat data for more responsive UI.'''

        attrs = []
        types = {}
        for attr in self.heat_attributes:
            if not attr.private:
                types[attr.name] = attr.field_type
                attrs.append(attr.frontend_repr())

        heat = self._racecontext.rhdata.get_heat(heat_id)
        heat_payload = {}
        heat_payload['id'] = heat.id
        heat_payload['displayname'] = heat.display_name
        heat_payload['name'] = heat.name
        heat_payload['auto_name'] = heat.auto_name
        heat_payload['class_id'] = heat.class_id
        heat_payload['group_id'] = heat.group_id
        heat_payload['order'] = heat.order
        heat_payload['status'] = heat.status
        heat_payload['auto_frequency'] = heat.auto_frequency
        heat_payload['active'] = heat.active
        heat_payload['next_round'] = self._racecontext.rhdata.get_max_round(heat.id)

        heat_payload['slots'] = []
        heatNodes = self._racecontext.rhdata.get_heatNodes_by_heat(heat.id)
        def heatNodeSorter(x):
            if not x.node_index:
                return -1
            return x.node_index
        heatNodes.sort(key=heatNodeSorter)

        is_dynamic = False
        for heatNode in heatNodes:
            current_node = {}
            current_node['id'] = heatNode.id
            current_node['node_index'] = heatNode.node_index
            current_node['pilot_id'] = heatNode.pilot_id
            # current_node['color'] = heatNode.color
            current_node['method'] = heatNode.method
            current_node['seed_rank'] = heatNode.seed_rank
            current_node['seed_id'] = heatNode.seed_id
            heat_payload['slots'].append(current_node)

            if current_node['method'] == ProgramMethod.HEAT_RESULT or current_node['method'] == ProgramMethod.CLASS_RESULT:
                is_dynamic = True

        heat_payload['dynamic'] = is_dynamic
        heat_payload['locked'] = bool(self._racecontext.rhdata.savedRaceMetas_has_heat(heat.id))

        heat_attributes = self._racecontext.rhdata.get_heat_attributes(heat)
        for attr in heat_attributes:
            if types.get(attr.name):
                heat_payload[attr.name] = attr.value != '0' if types.get(attr.name) == UIFieldType.CHECKBOX else attr.value

        emit_payload = {
            'heat': heat_payload
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_HEAT_EXPANDED, emit_payload)

        if ('nobroadcast' in params):
            emit('heat_expanded', emit_payload)
        elif ('noself' in params):
            emit('heat_expanded', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('heat_expanded', emit_payload)


    def emit_heat_list(self, **params):
        '''Emits heat list.'''

        heats = []
        for heat in self._racecontext.rhdata.get_heats():
            current_heat = {}
            current_heat['id'] = heat.id
            current_heat['displayname'] = heat.display_name
            current_heat['class_id'] = heat.class_id
            current_heat['group_id'] = heat.group_id
            current_heat['order'] = heat.order
            current_heat['status'] = heat.status
            current_heat['active'] = heat.active
            heats.append(current_heat)

        emit_payload = {
            'heats': heats,
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_HEAT_LIST, emit_payload)

        if ('nobroadcast' in params):
            emit('heat_list', emit_payload)
        elif ('noself' in params):
            emit('heat_list', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('heat_list', emit_payload)

    def emit_class_list(self, **params):
        '''Emits class list.'''

        current_classes = []
        for race_class in self._racecontext.rhdata.get_raceClasses():
            current_class = {}
            current_class['id'] = race_class.id
            current_class['displayname'] = race_class.display_name
            current_class['order'] = race_class.order
            current_classes.append(current_class)

        emit_payload = {
            'classes': current_classes,
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_CLASS_LIST, emit_payload)

        if ('nobroadcast' in params):
            emit('class_list', emit_payload)
        elif ('noself' in params):
            emit('class_list', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('class_list', emit_payload)

        if ('check_emit_small_event' in params):
            if len(self._racecontext.rhdata.get_heats()) <= self._racecontext.serverconfig.get_item_int('UI', 'smallEventThreshold'):
                self.emit_heat_data()

    def emit_heat_data(self, **params):
        '''Emits heat data.'''

        attrs = []
        types = {}
        for attr in self.heat_attributes:
            if not attr.private:
                types[attr.name] = attr.field_type
                attrs.append(attr.frontend_repr())

        heats = []
        for heat in self._racecontext.rhdata.get_heats():
            current_heat = {}
            current_heat['id'] = heat.id
            current_heat['displayname'] = heat.display_name
            current_heat['name'] = heat.name
            current_heat['auto_name'] = heat.auto_name
            current_heat['class_id'] = heat.class_id
            current_heat['group_id'] = heat.group_id
            current_heat['order'] = heat.order
            current_heat['status'] = heat.status
            current_heat['auto_frequency'] = heat.auto_frequency
            current_heat['active'] = heat.active
            current_heat['coop_best_time'] = RHUtils.format_secs_to_duration_str(heat.coop_best_time) \
                                    if isinstance(heat.coop_best_time, (int, float)) and \
                                                        heat.coop_best_time >= 0.001 else ''
            current_heat['coop_num_laps'] = heat.coop_num_laps
            current_heat['next_round'] = self._racecontext.rhdata.get_max_round(heat.id)

            current_heat['slots'] = []

            heatNodes = self._racecontext.rhdata.get_heatNodes_by_heat(heat.id)
            def heatNodeSorter(x):
                if not x.node_index:
                    return -1
                return x.node_index
            heatNodes.sort(key=heatNodeSorter)

            is_dynamic = False
            for heatNode in heatNodes:
                current_node = {}
                current_node['id'] = heatNode.id
                current_node['node_index'] = heatNode.node_index
                current_node['pilot_id'] = heatNode.pilot_id
                # current_node['color'] = heatNode.color
                current_node['method'] = heatNode.method
                current_node['seed_rank'] = heatNode.seed_rank
                current_node['seed_id'] = heatNode.seed_id
                current_heat['slots'].append(current_node)

                if current_node['method'] == ProgramMethod.HEAT_RESULT or current_node['method'] == ProgramMethod.CLASS_RESULT:
                    is_dynamic = True

            current_heat['dynamic'] = is_dynamic
            current_heat['locked'] = bool(self._racecontext.rhdata.savedRaceMetas_has_heat(heat.id))

            heat_attributes = self._racecontext.rhdata.get_heat_attributes(heat)
            for attr in heat_attributes:
                if types.get(attr.name):
                    current_heat[attr.name] = attr.value != '0' if types.get(attr.name) == UIFieldType.CHECKBOX else attr.value

            heats.append(current_heat)

        emit_payload = {
            'heats': heats,
            'attributes': attrs
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_HEAT_DATA, emit_payload)

        if ('nobroadcast' in params):
            emit('heat_data', emit_payload)
        elif ('noself' in params):
            emit('heat_data', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('heat_data', emit_payload)

    def emit_heat_attribute_types(self, **params):
        '''Emits heat attribute meta.'''

        attrs = []
        types = {}
        for attr in self.heat_attributes:
            if not attr.private:
                types[attr.name] = attr.field_type
                attrs.append(attr.frontend_repr())

        emit_payload = {
            'attributes': attrs
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_HEAT_DATA, emit_payload)

        if ('nobroadcast' in params):
            emit('heat_attribute_types', emit_payload)
        elif ('noself' in params):
            emit('heat_attribute_types', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('heat_attribute_types', emit_payload)

    def emit_recent_heats(self, class_id, limit, **params):
        '''Emits data of most recent heats class.'''

        types = {}
        for attr in self.heat_attributes:
            if not attr.private:
                types[attr.name] = attr.field_type

        heats = []
        for heat in self._racecontext.rhdata.get_recent_heats_by_class(class_id, limit):
            current_heat = {}
            current_heat['id'] = heat.id
            current_heat['displayname'] = heat.display_name
            current_heat['name'] = heat.name
            current_heat['auto_name'] = heat.auto_name
            current_heat['class_id'] = heat.class_id
            current_heat['group_id'] = heat.group_id
            current_heat['order'] = heat.order
            current_heat['status'] = heat.status
            current_heat['auto_frequency'] = heat.auto_frequency
            current_heat['active'] = heat.active
            current_heat['next_round'] = self._racecontext.rhdata.get_max_round(heat.id)
            current_heat['coop_best_time'] = RHUtils.format_secs_to_duration_str(heat.coop_best_time) \
                if isinstance(heat.coop_best_time, (int, float)) and \
                   heat.coop_best_time >= 0.001 else ''
            current_heat['coop_num_laps'] = heat.coop_num_laps

            current_heat['slots'] = []

            heatNodes = self._racecontext.rhdata.get_heatNodes_by_heat(heat.id)
            def heatNodeSorter(x):
                if not x.node_index:
                    return -1
                return x.node_index
            heatNodes.sort(key=heatNodeSorter)

            is_dynamic = False
            for heatNode in heatNodes:
                current_node = {}
                current_node['id'] = heatNode.id
                current_node['node_index'] = heatNode.node_index
                current_node['pilot_id'] = heatNode.pilot_id
                # current_node['color'] = heatNode.color
                current_node['method'] = heatNode.method
                current_node['seed_rank'] = heatNode.seed_rank
                current_node['seed_id'] = heatNode.seed_id
                current_heat['slots'].append(current_node)

                if current_node['method'] == ProgramMethod.HEAT_RESULT or current_node['method'] == ProgramMethod.CLASS_RESULT:
                    is_dynamic = True

            current_heat['dynamic'] = is_dynamic
            current_heat['locked'] = bool(self._racecontext.rhdata.savedRaceMetas_has_heat(heat.id))

            heat_attributes = self._racecontext.rhdata.get_heat_attributes(heat)
            for attr in heat_attributes:
                if types.get(attr.name):
                    current_heat[attr.name] = attr.value != '0' if types.get(attr.name) == UIFieldType.CHECKBOX else attr.value

            heats.append(current_heat)

        emit_payload = {
            'class': class_id,
            'heats': heats,
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_RECENT_HEAT_DATA, emit_payload)

        if ('nobroadcast' in params):
            emit('recent_heat_data', emit_payload)
        elif ('noself' in params):
            emit('recent_heat_data', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('recent_heat_data', emit_payload)

    def emit_class_data(self, **params):
        '''Emits class data.'''

        attrs = []
        types = {}
        for attr in self.raceclass_attributes:
            if not attr.private:
                types[attr.name] = attr.field_type
                attrs.append(attr.frontend_repr())

        current_classes = []
        for race_class in self._racecontext.rhdata.get_raceClasses():
            current_class = {}
            current_class['id'] = race_class.id
            current_class['name'] = race_class.name
            current_class['displayname'] = race_class.display_name
            current_class['description'] = race_class.description
            current_class['format'] = race_class.format_id
            current_class['win_condition'] = race_class.win_condition
            current_class['ranksettings'] = json.loads(race_class.rank_settings) if race_class.rank_settings else None
            current_class['rounds'] = race_class.rounds
            current_class['heat_advance_type'] = race_class.heat_advance_type
            current_class['round_type'] = race_class.round_type
            current_class['order'] = race_class.order
            current_class['locked'] = self._racecontext.rhdata.savedRaceMetas_has_raceClass(race_class.id)

            if current_class['win_condition'] and race_class.win_condition in self._racecontext.raceclass_rank_manager.methods:
                current_class['rank_method_label'] = self._racecontext.raceclass_rank_manager.methods[race_class.win_condition].label

            raceclass_attributes = self._racecontext.rhdata.get_raceclass_attributes(race_class)
            for attr in raceclass_attributes:
                if types.get(attr.name):
                    current_class[attr.name] = attr.value != '0' if types.get(attr.name) == UIFieldType.CHECKBOX else attr.value

            current_classes.append(current_class)

        emit_payload = {
            'classes': current_classes,
            'attributes': attrs
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_CLASS_DATA, emit_payload)

        if ('nobroadcast' in params):
            emit('class_data', emit_payload)
        elif ('noself' in params):
            emit('class_data', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('class_data', emit_payload)

    def emit_format_data(self, **params):
        '''Emits format data.'''
        formats = []
        for race_format in self._racecontext.rhdata.get_raceFormats():
            raceformat = {}
            raceformat['id'] = race_format.id
            raceformat['name'] = race_format.name
            raceformat['unlimited_time'] = race_format.unlimited_time
            raceformat['race_time_sec'] = race_format.race_time_sec
            raceformat['lap_grace_sec'] = race_format.lap_grace_sec
            raceformat['staging_fixed_tones'] = race_format.staging_fixed_tones
            raceformat['staging_delay_tones'] = race_format.staging_delay_tones
            raceformat['start_delay_min'] = race_format.start_delay_min_ms
            raceformat['start_delay_max'] = race_format.start_delay_max_ms
            raceformat['number_laps_win'] = race_format.number_laps_win
            raceformat['win_condition'] = race_format.win_condition
            raceformat['team_racing_mode'] = int(race_format.team_racing_mode) if race_format.team_racing_mode else RacingMode.INDIVIDUAL
            raceformat['start_behavior'] = race_format.start_behavior
            raceformat['locked'] = self._racecontext.rhdata.savedRaceMetas_has_raceFormat(race_format.id)
            formats.append(raceformat)

            if race_format.points_method:
                points_method = json.loads(race_format.points_method)
                raceformat['points_method'] = points_method['t']
                if 's' in points_method:
                    raceformat['points_settings'] = points_method['s']
                else:
                    raceformat['points_settings'] = None
            else:
                raceformat['points_method'] = None
                raceformat['points_settings'] = None

        emit_payload = {
            'formats': formats,
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_FORMAT_DATA, emit_payload)

        if ('nobroadcast' in params):
            emit('format_data', emit_payload)
        elif ('noself' in params):
            emit('format_data', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('format_data', emit_payload)

    def emit_pilot_list(self, **params):
        '''Emits pilot data.'''
        pilots_list = []

        for pilot in self._racecontext.rhdata.get_pilots():
            pilot_data = {
                'pilot_id': pilot.id,
                'callsign': pilot.callsign,
                'team': pilot.team,
                'name': pilot.name,
                'color': pilot.color,
            }
            pilots_list.append(pilot_data)

        if self._racecontext.serverconfig.get_item('UI', 'pilotSort') == 'callsign':
            pilots_list.sort(key=lambda x: (x['callsign'].casefold(), x['name'].casefold()))
        else:
            pilots_list.sort(key=lambda x: (x['name'].casefold(), x['callsign'].casefold()))

        emit_payload = {
            'pilots': pilots_list,
            'pilotSort': self._racecontext.serverconfig.get_item('UI', 'pilotSort'),
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_PILOT_LIST, emit_payload)

        if ('nobroadcast' in params):
            emit('pilot_data', emit_payload)
        elif ('noself' in params):
            emit('pilot_data', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('pilot_data', emit_payload)

    def emit_pilot_data(self, **params):
        '''Emits pilot data.'''
        pilots_list = []

        attrs = []
        types = {}
        for attr in self.pilot_attributes:
            if not attr.private:
                types[attr.name] = attr.field_type
                attrs.append(attr.frontend_repr())

        for pilot in self._racecontext.rhdata.get_pilots():
            opts_str = '' # create team-options string for each pilot, with current team selected
            for name in self._racecontext.rhdata.TEAM_NAMES_LIST:
                opts_str += '<option value="' + name + '"'
                if name == pilot.team:
                    opts_str += ' selected'
                opts_str += '>' + name + '</option>'

            locked = self._racecontext.rhdata.savedPilotRaces_has_pilot(pilot.id)

            pilot_data = {
                'pilot_id': pilot.id,
                'callsign': pilot.callsign,
                'team': pilot.team,
                'phonetic': pilot.phonetic,
                'name': pilot.name,
                'active': pilot.active,
                'team_options': opts_str,
                'color': pilot.color,
                'locked': locked,
            }

            pilot_attributes = self._racecontext.rhdata.get_pilot_attributes(pilot)
            for attr in pilot_attributes:
                if types.get(attr.name):
                    pilot_data[attr.name] = attr.value != '0' if types.get(attr.name) == UIFieldType.CHECKBOX else attr.value

            pilots_list.append(pilot_data)

        if self._racecontext.serverconfig.get_item('UI', 'pilotSort') == 'callsign':
            pilots_list.sort(key=lambda x: (x['callsign'].casefold(), x['name'].casefold()))
        else:
            pilots_list.sort(key=lambda x: (x['name'].casefold(), x['callsign'].casefold()))

        emit_payload = {
            'pilots': pilots_list,
            'pilotSort': self._racecontext.serverconfig.get_item('UI', 'pilotSort'),
            'attributes': attrs
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_PILOT_DATA, emit_payload)

        if ('nobroadcast' in params):
            emit('pilot_data', emit_payload)
        elif ('noself' in params):
            emit('pilot_data', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('pilot_data', emit_payload)

    def emit_seat_data(self, **params):
        """Emits seat data."""
        seat_list = []

        seatColorOpt = self._racecontext.serverconfig.get_item('LED', 'seatColors')
        if seatColorOpt:
            seatColors = seatColorOpt
        else:
            seatColors = self._racecontext.serverstate.seat_color_defaults

        for seat in range(self._racecontext.race.num_nodes):
            seat_list.append({
                'seat_id': seat,
                'color': seatColors[seat % len(seatColors)]
            })

        emit_payload = {
            'seats': seat_list,
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_SEAT_DATA, emit_payload)

        if ('nobroadcast' in params):
            emit('seat_data', emit_payload)
        elif ('noself' in params):
            emit('seat_data', emit_payload, broadcast=True, include_self=False)
        else:
            self._socket.emit('seat_data', emit_payload)

    def emit_current_heat(self, **params):
        '''Emits the current heat.'''
        heat_data = self._racecontext.rhdata.get_heat(self._racecontext.race.current_heat)

        heatNode_data = {}
        for idx in range(self._racecontext.race.num_nodes):
            heatNode_data[idx] = {
                'pilot_id': None,
                'callsign': None,
                'heatNodeColor': None,
                'pilotColor': None,
                'activeColor': self._racecontext.race.seat_colors[idx]
            }

        heat_format = None

        if heat_data:
            heat_class = heat_data.class_id

            for heatNode in self._racecontext.rhdata.get_heatNodes_by_heat(self._racecontext.race.current_heat):
                if heatNode.node_index is not None and heatNode.node_index < len(heatNode_data):
                    heatNode_data[heatNode.node_index]['pilot_id'] = heatNode.pilot_id
                    heatNode_data[heatNode.node_index]['heatNodeColor'] = heatNode.color

                    pilot = self._racecontext.rhdata.get_pilot(heatNode.pilot_id)
                    if pilot:
                        heatNode_data[heatNode.node_index]['callsign'] = pilot.callsign
                        heatNode_data[heatNode.node_index]['pilotColor'] = pilot.color

            if heat_data.class_id != RHUtils.CLASS_ID_NONE:
                heat_format = self._racecontext.rhdata.get_raceClass(heat_data.class_id).format_id

        else:
            # Practice mode
            heat_class = RHUtils.CLASS_ID_NONE

            profile_freqs = json.loads(self._racecontext.race.profile.frequencies)

            for idx in range(self._racecontext.race.num_nodes):
                if (profile_freqs["b"][idx] and profile_freqs["c"][idx]):
                    callsign = profile_freqs["b"][idx] + str(profile_freqs["c"][idx])
                else:
                    callsign = str(profile_freqs["f"][idx])

                heatNode_data[idx]['callsign'] = callsign

        emit_payload = {
            'current_heat': self._racecontext.race.current_heat,
            'heatNodes': heatNode_data,
            'heat_format': heat_format,
            'heat_class': heat_class,
        }
        if self._racecontext.race.current_heat:

            emit_payload['coop_best_time'] = RHUtils.format_secs_to_duration_str(heat_data.coop_best_time) \
                if isinstance(heat_data.coop_best_time, (int, float)) and \
                   heat_data.coop_best_time >= 0.001 else ''
            emit_payload['coop_num_laps'] = heat_data.coop_num_laps

            if heat_class:
                race_class = self._racecontext.rhdata.get_raceClass(heat_class)
                if race_class.round_type == RoundType.GROUPED:
                    emit_payload['next_round'] = heat_data.group_id + 1
                else:
                    emit_payload['next_round'] = self._racecontext.rhdata.get_round_num_for_heat(heat_data.id)
            else:
                emit_payload['next_round'] = self._racecontext.rhdata.get_round_num_for_heat(heat_data.id)
        else:
            emit_payload['next_round'] = None

        if ('nobroadcast' in params):
            emit('current_heat', emit_payload)
        else:
            self._socket.emit('current_heat', emit_payload)

    def emit_phonetic_data(self, pilot_id, lap_id, lap_time, team_phonetic, leader_flag=False, \
                           node_finished=False, node_index=None, team_short_phonetic=None, **params):
        '''Emits phonetic data.'''
        raw_time = lap_time
        phonetic_time = RHUtils.format_phonetic_time_to_str(lap_time, self._racecontext.serverconfig.get_item('UI', 'timeFormatPhonetic'))

        emit_payload = {
            'lap': lap_id,
            'raw_time': raw_time,
            'phonetic': phonetic_time,
            'team_phonetic' : team_phonetic,
            'team_short_phonetic': team_short_phonetic,
            'leader_flag' : leader_flag,
            'node_finished': node_finished,
        }

        pilot = self._racecontext.rhdata.get_pilot(pilot_id)
        if pilot:
            emit_payload['pilot'] = pilot.phonetic
            emit_payload['callsign'] = pilot.callsign
            emit_payload['pilot_id'] = pilot.id
        elif node_index is not None:
            profile_freqs = json.loads(self._racecontext.race.profile.frequencies)

            if (profile_freqs["b"][node_index] and profile_freqs["c"][node_index]):
                callsign = profile_freqs["b"][node_index] + str(profile_freqs["c"][node_index])
            else:
                callsign = str(profile_freqs["f"][node_index])

            emit_payload['pilot'] = callsign
            emit_payload['callsign'] = callsign
            emit_payload['pilot_id'] = None
        else:
            emit_payload['pilot'] = None
            emit_payload['callsign'] = None
            emit_payload['pilot_id'] = None

        emit_payload = self._filters.run_filters(Flt.EMIT_PHONETIC_DATA, emit_payload)

        if ('nobroadcast' in params):
            emit('phonetic_data', emit_payload)
        else:
            self._socket.emit('phonetic_data', emit_payload)

    def emit_phonetic_leader(self, pilot_id, **params):
        '''Emits phonetic pilot name for race leader.'''
        pilot = self._racecontext.rhdata.get_pilot(pilot_id)
        emit_payload = {}
        if pilot:
            emit_payload['pilot'] = pilot.phonetic
            emit_payload['callsign'] = pilot.callsign
            emit_payload['pilot_id'] = pilot.id

        emit_payload = self._filters.run_filters(Flt.EMIT_PHONETIC_LEADER, emit_payload)

        if ('nobroadcast' in params):
            emit('phonetic_leader', emit_payload)
        else:
            self._socket.emit('phonetic_leader', emit_payload)

    def emit_race_saved(self, new_race, race_data, **params):
        emit_payload = {
            'race_id': new_race.id,
            'heat_id': new_race.heat_id,
            'class_id': new_race.class_id,
            'format_id': new_race.format_id,
            'pilot_ids': [race_data[x]['pilot_id'] for x in race_data]
        }

        if ('nobroadcast' in params):
            emit('race_saved', emit_payload)
        else:
            self._socket.emit('race_saved', emit_payload)
        
    def emit_first_pass_registered(self, node_idx, **params):
        '''Emits when first pass (lap 0) is registered during a race'''
        emit_payload = {
            'node_index': node_idx,
        }
        self._events.trigger(Evt.RACE_FIRST_PASS, {
            'node_index': node_idx,
            })

        if ('nobroadcast' in params):
            emit('first_pass_registered', emit_payload)
        else:
            self._socket.emit('first_pass_registered', emit_payload)

    def emit_phonetic_text(self, text_str, domain=False, winner_flag=False, **params):
        '''Emits given phonetic text.'''
        emit_payload = {
            'text': text_str,
            'domain': domain,
            'winner_flag': winner_flag
        }

        emit_payload = self._filters.run_filters(Flt.EMIT_PHONETIC_TEXT, emit_payload)

        if ('nobroadcast' in params):
            emit('phonetic_text', emit_payload)
        else:
            self._socket.emit('phonetic_text', emit_payload)

    def emit_phonetic_split(self, split_data, **params):
        '''Emits phonetic split-pass data.'''
        name_callout_flag = split_data.get('name_callout_flag', True)
        time_callout_flag = split_data.get('time_callout_flag', True)
        speed_callout_flag = split_data.get('speed_callout_flag', True)
        if name_callout_flag or time_callout_flag or speed_callout_flag:
            pilot = self._racecontext.rhdata.get_pilot(split_data.get('pilot_id', RHUtils.PILOT_ID_NONE))
            phonetic_name = (pilot.phonetic or pilot.callsign) if name_callout_flag and pilot else ''
            split_time = split_data.get('split_time')
            phonetic_time = RHUtils.format_phonetic_time_to_str(split_time, self._racecontext.serverconfig.get_item('UI', 'timeFormatPhonetic')) \
                            if (time_callout_flag and split_time) else None
            split_speed = split_data.get('split_speed')
            phonetic_speed = "{:.1f}".format(split_speed) if  (speed_callout_flag and split_speed) else None
            split_id = split_data.get('split_id', -1)
            emit_payload = {
                'pilot_name': phonetic_name,
                'split_id': str(split_id+1),
                'split_time': phonetic_time,
                'split_speed': phonetic_speed
            }

            emit_payload = self._filters.run_filters(Flt.EMIT_PHONETIC_SPLIT, emit_payload)

            if ('nobroadcast' in params):
                emit('phonetic_split_call', emit_payload)
            else:
                self._socket.emit('phonetic_split_call', emit_payload)

    def emit_split_pass_info(self, split_data):
        self._racecontext.race.clear_results()
        self.emit_current_laps()  # update all laps on the race page
        self.emit_phonetic_split(split_data)

    def emit_enter_at_level(self, node, **params):
        '''Emits enter-at level for given node.'''
        emit_payload = {
            'node_index': node.index,
            'level': node.enter_at_level
        }
        if ('nobroadcast' in params):
            emit('node_enter_at_level', emit_payload)
        else:
            self._socket.emit('node_enter_at_level', emit_payload)

    def emit_exit_at_level(self, node, **params):
        '''Emits exit-at level for given node.'''
        emit_payload = {
            'node_index': node.index,
            'level': node.exit_at_level
        }
        if ('nobroadcast' in params):
            emit('node_exit_at_level', emit_payload)
        else:
            self._socket.emit('node_exit_at_level', emit_payload)

    def emit_node_crossing_change(self, node, **params):
        '''Emits crossing-flag change for given node.'''
        emit_payload = {
            'node_index': node.index,
            'crossing_flag': node.crossing_flag
        }
        if ('nobroadcast' in params):
            emit('node_crossing_change', emit_payload)
        else:
            self._socket.emit('node_crossing_change', emit_payload)

    def emit_cluster_connect_change(self, connect_flag, **params):
        '''Emits connect/disconnect tone for cluster timer.'''
        emit_payload = {
            'connect_flag': connect_flag
        }
        if ('nobroadcast' in params):
            emit('cluster_connect_change', emit_payload)
        else:
            self._socket.emit('cluster_connect_change', emit_payload)

    def emit_play_beep_tone(self, duration, frequency, volume=None, toneType=None, **params):
        '''Emits beep/tone.'''
        emit_payload = {
            'duration': duration,
            'frequency': frequency,
            'volume': volume,
            'toneType': toneType
        }
        if ('nobroadcast' in params):
            emit('play_beep_tone', emit_payload)
        else:
            self._socket.emit('play_beep_tone', emit_payload)

    def emit_callouts(self):
        callouts = self._racecontext.serverconfig.get_item('USER', 'voiceCallouts')
        if callouts:
            emit('callouts', json.loads(callouts))

    def emit_imdtabler_page(self, IMDTABLER_JAR_NAME, Use_imdtabler_jar_flag, **_params):
        '''Emits IMDTabler page, using current profile frequencies.'''
        if Use_imdtabler_jar_flag:
            try:                          # get IMDTabler version string
                imdtabler_ver = subprocess.check_output( \
                                    'java -jar ' + IMDTABLER_JAR_NAME + ' -v', shell=True).decode("utf-8").rstrip()
                profile_freqs = json.loads(self._racecontext.race.profile.frequencies)
                fi_list = list(OrderedDict.fromkeys(profile_freqs['f'][:self._racecontext.race.num_nodes]))  # remove duplicates
                fs_list = []
                for val in fi_list:  # convert list of integers to list of strings
                    if val > 0:      # drop any zero entries
                        fs_list.append(str(val))
                self.emit_imdtabler_data(IMDTABLER_JAR_NAME, fs_list, imdtabler_ver)
            except Exception:
                logger.exception('emit_imdtabler_page exception')

    def emit_imdtabler_data(self, IMDTABLER_JAR_NAME, fs_list, imdtabler_ver=None, **params):
        '''Emits IMDTabler data for given frequencies.'''
        try:
            imdtabler_data = None
            if len(fs_list) > 2:  # if 3+ then invoke jar; get response
                imdtabler_data = subprocess.check_output( \
                            'java -jar ' + IMDTABLER_JAR_NAME + ' -t ' + ' '.join(fs_list), shell=True).decode("utf-8")
        except Exception:
            imdtabler_data = None
            logger.exception('emit_imdtabler_data exception')
        emit_payload = {
            'freq_list': ' '.join(fs_list),
            'table_data': imdtabler_data,
            'version_str': imdtabler_ver
        }
        if ('nobroadcast' in params):
            emit('imdtabler_data', emit_payload)
        else:
            self._socket.emit('imdtabler_data', emit_payload)

    def emit_imdtabler_rating(self, IMDTABLER_JAR_NAME):
        '''Emits IMDTabler rating for current profile frequencies.'''
        try:
            profile_freqs = json.loads(self._racecontext.race.profile.frequencies)
            imd_val = None
            fi_list = list(OrderedDict.fromkeys(profile_freqs['f'][:self._racecontext.race.num_nodes]))  # remove duplicates
            fs_list = []
            for val in fi_list:  # convert list of integers to list of strings
                if val > 0:      # drop any zero entries
                    fs_list.append(str(val))
            if len(fs_list) > 2:
                imd_val = subprocess.check_output(  # invoke jar; get response
                            'java -jar ' + IMDTABLER_JAR_NAME + ' -r ' + ' '.join(fs_list), shell=True).decode("utf-8").rstrip()
        except Exception:
            imd_val = None
            logger.exception('emit_imdtabler_rating exception')
        emit_payload = {
                'imd_rating': imd_val
            }
        self._socket.emit('imdtabler_rating', emit_payload)

    @catchLogExceptionsWrapper
    def emit_pass_record(self, node, lap_time_stamp):
        '''Emits 'pass_record' message (will be consumed by primary timer in cluster, livetime, etc).'''
        payload = {
            'node': node.index,
            'frequency': node.frequency,
            'timestamp': lap_time_stamp + self._racecontext.race.start_time_epoch_ms
        }
        self._racecontext.cluster.emit_cluster_msg_to_primary(self._socket, 'pass_record', payload)

    def emit_vrx_list(self, *_args, **params):
        ''' get list of connected VRx devices '''
        if self._racecontext.vrx_manager.isEnabled():
            emit_payload = {
                'enabled': True,
                'controllers': self._racecontext.vrx_manager.getControllerStatus(),
                'devices': self._racecontext.vrx_manager.getAllDeviceStatus()
            }
        else:
            emit_payload = {
                'enabled': False,
                'controllers': None,
                'devices': None
            }

        if ('nobroadcast' in params):
            emit('vrx_list', emit_payload)
        else:
            self._socket.emit('vrx_list', emit_payload)

    def emit_exporter_list(self):
        '''List Database Exporters'''

        emit_payload = {
            'exporters': []
        }

        for name, exp in self._racecontext.export_manager.exporters.items():
            emit_payload['exporters'].append({
                'name': name,
                'label': exp.label
            })

        emit('exporter_list', emit_payload)

    def emit_importer_list(self):
        '''List Database Importers'''

        emit_payload = {
            'importers': []
        }

        for name, imp in self._racecontext.import_manager.importers.items():
            emit_payload['importers'].append({
                'name': name,
                'label': imp.label,
                'settings': [field.frontend_repr() for field in imp.settings] if imp.settings else None
            })

        emit('importer_list', emit_payload)

    def emit_heatgenerator_list(self):
        '''List Heat Generators'''

        emit_payload = {
            'generators': []
        }

        for name, gen in self._racecontext.heat_generate_manager.generators.items():
            emit_payload['generators'].append({
                'name': name,
                'label': gen.label,
                'settings': [field.frontend_repr() for field in gen.settings] if gen.settings else None
            })

        emit('heatgenerator_list', emit_payload)

    def emit_raceclass_rank_method_list(self):
        '''List Race Class Rank Methods'''

        emit_payload = {
            'methods': []
        }

        for name, method in self._racecontext.raceclass_rank_manager.methods.items():
            emit_payload['methods'].append({
                'name': name,
                'label': method.label,
                'settings': [field.frontend_repr() for field in method.settings] if method.settings else None
            })

        emit('raceclass_rank_method_list', emit_payload)

    def emit_race_points_method_list(self):
        '''List Race Points Methods'''

        emit_payload = {
            'methods': []
        }

        for name, method in self._racecontext.race_points_manager.methods.items():
            emit_payload['methods'].append({
                'name': name,
                'label': method.label,
                'settings': [field.frontend_repr() for field in method.settings] if method.settings else None
            })

        emit('race_points_method_list', emit_payload)

    def get_pilot_freq_info(self, profile_freqs, freq_val, node_idx):
        try:       # if node freq matches then return band/channel and frequency
            if freq_val == profile_freqs["f"][node_idx]:
                band = profile_freqs["b"][node_idx]
                chan = profile_freqs["c"][node_idx]
                if band and chan:
                    return "{}{} {}".format(band, chan, freq_val)
        except:
            pass
        # if node freq does not match then just return frequency
        return "{}".format(freq_val)

    def emit_restart_required(self, **params):
        ''' Emits restart required message to all clients '''
        self._socket.emit('restart_required')
