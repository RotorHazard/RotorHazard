''' Class to access race functions and details '''
import functools
from Database import LapSource

API_VERSION_MAJOR = 1
API_VERSION_MINOR = 3

import dataclasses
import json
import inspect
import copy
import logging
import RHUtils
from RHUI import UIField, UIFieldType
from eventmanager import Evt

logger = logging.getLogger(__name__)

from FlaskAppObj import APP
APP.app_context().push()

class RHAPI():
    def __init__(self, race_context):
        self.API_VERSION_MAJOR = API_VERSION_MAJOR
        self.API_VERSION_MINOR = API_VERSION_MINOR
        self.server_info = None

        self._racecontext = race_context

        self.ui = UserInterfaceAPI(self._racecontext)
        self.fields = FieldsAPI(self._racecontext)
        self.db = DatabaseAPI(self._racecontext)
        self.io = IOAPI(self._racecontext)
        self.heatgen = HeatGenerateAPI(self._racecontext)
        self.classrank = ClassRankAPI(self._racecontext)
        self.points = PointsAPI(self._racecontext)
        self.led = LEDAPI(self._racecontext)
        self.vrxcontrol = VRxControlAPI(self._racecontext)
        self.race = RaceAPI(self._racecontext)
        self.language = LanguageAPI(self._racecontext)
        self.interface = HardwareInterfaceAPI(self._racecontext)
        self.config = ServerConfigAPI(self._racecontext)
        self.sensors = SensorsAPI(self._racecontext)
        self.eventresults = EventResultsAPI(self._racecontext)
        self.events = EventsAPI(self._racecontext)
        self.server = ServerAPI(self._racecontext)
        self.filters = FilterAPI(self._racecontext)
        self.utils = UtilsAPI(self._racecontext)

        self.__ = self.language.__ # shortcut access

# Wrapper to be used as a decorator on API functions that do database calls,
#  so the database session is cleaned up on exit (prevents DB-file handles left open).
def callWithDatabaseWrapper(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up
            return func(self, *args, **kwargs)
    return wrapper


#
# UI helpers
#
class UserInterfaceAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    # UI Panel
    @property
    def panels(self):
        return self._racecontext.rhui.ui_panels

    def register_panel(self, name, label, page, order=0, open = False):
        return self._racecontext.rhui.register_ui_panel(name, label, page, order, open)

    # Quick button
    def register_quickbutton(self, panel, name, label, function, args=None):
        return self._racecontext.rhui.register_quickbutton(panel, name, label, function, args)

    # Markdown
    def register_markdown(self, panel, name, desc):
        return self._racecontext.rhui.register_markdown(panel, name, desc)

    # Blueprint
    def blueprint_add(self, blueprint):
        return self._racecontext.rhui.add_blueprint(blueprint)

    # Messaging
    def message_speak(self, message):
        self._racecontext.rhui.emit_phonetic_text(message)

    def message_notify(self, message):
        self._racecontext.rhui.emit_priority_message(message, False)

    def message_alert(self, message):
        self._racecontext.rhui.emit_priority_message(message, True)

    def clear_messages(self):
        self._racecontext.rhui.emit_clear_priority_messages()

    # Socket
    def socket_listen(self, message, handler):
        self._racecontext.rhui.socket_listen(message, handler)

    def socket_send(self, message, data):
        self._racecontext.rhui.socket_send(message, data)

    def socket_broadcast(self, message, data):
        self._racecontext.rhui.socket_broadcast(message, data)

    # Broadcasts
    @callWithDatabaseWrapper
    def broadcast_ui(self, page):
        self._racecontext.rhui.emit_ui(page)

    @callWithDatabaseWrapper
    def broadcast_frequencies(self):
        self._racecontext.rhui.emit_frequency_data()

    @callWithDatabaseWrapper
    def broadcast_pilots(self):
        self._racecontext.rhui.emit_pilot_data()

    @callWithDatabaseWrapper
    def broadcast_heats(self):
        self._racecontext.rhui.emit_heat_data()

    @callWithDatabaseWrapper
    def broadcast_raceclasses(self):
        self._racecontext.rhui.emit_class_data()

    @callWithDatabaseWrapper
    def broadcast_raceformats(self):
        self._racecontext.rhui.emit_format_data()

    @callWithDatabaseWrapper
    def broadcast_current_heat(self):
        self._racecontext.rhui.emit_current_heat()

    @callWithDatabaseWrapper
    def broadcast_frequencyset(self):
        self._racecontext.rhui.emit_node_tuning()

    @callWithDatabaseWrapper
    def broadcast_race_status(self):
        self._racecontext.rhui.emit_race_status()


#
# Data structures
#
class FieldsAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    # Pilot Attribute
    @property
    def pilot_attributes(self):
        return self._racecontext.rhui.pilot_attributes

    def register_pilot_attribute(self, field:UIField):
        return self._racecontext.rhui.register_pilot_attribute(field)

    # Heat Attribute
    @property
    def heat_attributes(self):
        return self._racecontext.rhui.heat_attributes

    def register_heat_attribute(self, field:UIField):
        return self._racecontext.rhui.register_heat_attribute(field)

    # Race Class Attribute
    @property
    def raceclass_attributes(self):
        return self._racecontext.rhui.raceclass_attributes

    def register_raceclass_attribute(self, field:UIField):
        return self._racecontext.rhui.register_raceclass_attribute(field)

    # Race Attribute
    @property
    def race_attributes(self):
        return self._racecontext.rhui.savedrace_attributes

    def register_race_attribute(self, field:UIField):
        return self._racecontext.rhui.register_savedrace_attribute(field)

    # Race Attribute
    @property
    def raceformat_attributes(self):
        return self._racecontext.rhui.raceformat_attributes

    def register_raceformat_attribute(self, field:UIField):
        return self._racecontext.rhui.register_raceformat_attribute(field)

    # General Setting
    @property
    def options(self):
        return self._racecontext.rhui.general_settings

    def register_option(self, field:UIField, panel=None, order=0):
        return self._racecontext.rhui.register_general_setting(field, panel, order)


#
# Database Access
#
class DatabaseAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    # Global

    @callWithDatabaseWrapper
    def reset_all(self):
        return self._racecontext.rhdata.reset_all()

    # Pilot

    @property
    @callWithDatabaseWrapper
    def pilots(self):
        return self._racecontext.rhdata.get_pilots()

    @callWithDatabaseWrapper
    def pilot_by_id(self, pilot_id):
        return self._racecontext.rhdata.get_pilot(pilot_id)

    @callWithDatabaseWrapper
    def pilot_attributes(self, pilot_or_id):
        return self._racecontext.rhdata.get_pilot_attributes(pilot_or_id)

    @callWithDatabaseWrapper
    def pilot_attribute_value(self, pilot_or_id, name, default_value=None):
        for field in self._racecontext.rhui.pilot_attributes:
            if field.name == name:
                return self._racecontext.rhdata.get_pilot_attribute_value(pilot_or_id, field.name, field.value)
        else:
            return self._racecontext.rhdata.get_pilot_attribute_value(pilot_or_id, name, default_value)

    @callWithDatabaseWrapper
    def pilot_ids_by_attribute(self, name, value):
        return self._racecontext.rhdata.get_pilot_id_by_attribute(name, value)

    @callWithDatabaseWrapper
    def pilot_add(self, name=None, callsign=None, phonetic=None, team=None, color=None):
        #TODO: attribute support
        data = {}

        for name, value in [
            ('callsign', callsign), 
            ('phonetic', phonetic),
            ('name', name),
            ('team', team),
            ('color', color),
            ]:
            if value is not None:
                data[name] = value

        return self._racecontext.rhdata.add_pilot(data)

    @callWithDatabaseWrapper
    def pilot_alter(self, pilot_id, name=None, callsign=None, phonetic=None, team=None, color=None, attributes=None):
        data = {}

        if isinstance(attributes, dict):
            data['pilot_id'] = pilot_id
            for key, value in attributes.items():
                data['pilot_attr'] = key
                data['value'] = value
                self._racecontext.rhdata.alter_pilot(data)

            data = {}

        for name, value in [
            ('callsign', callsign), 
            ('phonetic', phonetic),
            ('name', name),
            ('team_name', team),
            ('color', color),
            ]:
            if value is not None:
                data[name] = value

        if data:
            data['pilot_id'] = pilot_id
            return self._racecontext.rhdata.alter_pilot(data)

    @callWithDatabaseWrapper
    def pilot_delete(self, pilot_or_id):
        return self._racecontext.rhdata.delete_pilot(pilot_or_id)

    @callWithDatabaseWrapper
    def pilots_reset(self):
        return self._racecontext.rhdata.reset_pilots()

    # Heat

    @property
    @callWithDatabaseWrapper
    def heats(self):
        return self._racecontext.rhdata.get_heats()

    @callWithDatabaseWrapper
    def heat_by_id(self, heat_id):
        return self._racecontext.rhdata.get_heat(heat_id)

    @callWithDatabaseWrapper
    def heat_attributes(self, heat_or_id):
        return self._racecontext.rhdata.get_heat_attributes(heat_or_id)

    @callWithDatabaseWrapper
    def heat_attribute_value(self, heat_or_id, name, default_value=None):
        for field in self._racecontext.rhui.heat_attributes:
            if field.name == name:
                return self._racecontext.rhdata.get_heat_attribute_value(heat_or_id, field.name, field.value)
        else:
            return self._racecontext.rhdata.get_heat_attribute_value(heat_or_id, name, default_value)

    @callWithDatabaseWrapper
    def heat_ids_by_attribute(self, name, value):
        return self._racecontext.rhdata.get_heat_id_by_attribute(name, value)

    @callWithDatabaseWrapper
    def heats_by_class(self, raceclass_id):
        return self._racecontext.rhdata.get_heats_by_class(raceclass_id)

    @callWithDatabaseWrapper
    def heat_results(self, heat_or_id):
        return self._racecontext.rhdata.get_results_heat(heat_or_id)

    @callWithDatabaseWrapper
    def heat_max_round(self, heat_id):
        return self._racecontext.rhdata.get_max_round(heat_id)

    @callWithDatabaseWrapper
    def heat_add(self, name=None, raceclass=None, auto_frequency=None):
        data = {}

        for name, value in [
            ('name', name),
            ('class_id', raceclass),
            ('auto_frequency', auto_frequency),
            ]:
            if value is not None:
                data[name] = value

        return self._racecontext.rhdata.add_heat(data)

    @callWithDatabaseWrapper
    def heat_duplicate(self, source_heat_or_id, dest_class=None):
        if dest_class:
            return self._racecontext.rhdata.duplicate_heat(source_heat_or_id, dest_class=dest_class)
        else:
            return self._racecontext.rhdata.duplicate_heat(source_heat_or_id)

    @callWithDatabaseWrapper
    def heat_alter(self, heat_id, name=None, raceclass=None, auto_frequency=None, status=None, attributes=None):
        data = {}

        if isinstance(attributes, dict):
            data['heat'] = heat_id
            for key, value in attributes.items():
                data['heat_attr'] = key
                data['value'] = value
                self._racecontext.rhdata.alter_heat(data)

            data = {}

        for name, value in [
            ('name', name),
            ('class', raceclass),
            ('auto_frequency', auto_frequency),
            ('status', status),
            ]:
            if value is not None:
                data[name] = value

        if data:
            data['heat'] = heat_id
            return self._racecontext.rhdata.alter_heat(data)

    @callWithDatabaseWrapper
    def heat_delete(self, heat_or_id):
        return self._racecontext.rhdata.delete_heat(heat_or_id)

    @callWithDatabaseWrapper
    def heats_reset(self):
        return self._racecontext.rhdata.reset_heats()

    # Heat -> Slots

    @property
    @callWithDatabaseWrapper
    def slots(self):
        return self._racecontext.rhdata.get_heatNodes()

    @callWithDatabaseWrapper
    def slots_by_heat(self, heat_id):
        return self._racecontext.rhdata.get_heatNodes_by_heat(heat_id)

    @callWithDatabaseWrapper
    def slot_alter(self, slot_id, method=None, pilot=None, seed_heat_id=None, seed_raceclass_id=None, seed_rank=None):
        data = {}

        for name, value in [
            ('pilot', pilot),
            ('method', method),
            ('seed_heat_id', seed_heat_id),
            ('seed_class_id', seed_raceclass_id),
            ('seed_rank', seed_rank),
            ]:
            if value is not None:
                data[name] = value

        if data:
            # resolve heat id so alteration can pass through alter_heat 
            slot = self._racecontext.rhdata.get_heatNode(slot_id)
            heat_id = slot.heat_id

            data['heat'] = heat_id
            data['slot_id'] = slot_id
            return self._racecontext.rhdata.alter_heat(data)

    @callWithDatabaseWrapper
    def slots_alter_fast(self, slot_list):
        # !! Unsafe for general use !!
        return self._racecontext.rhdata.alter_heatNodes_fast(slot_list)

    # Race Class

    @property
    @callWithDatabaseWrapper
    def raceclasses(self):
        return self._racecontext.rhdata.get_raceClasses()

    @callWithDatabaseWrapper
    def raceclass_by_id(self, raceclass_id):
        return self._racecontext.rhdata.get_raceClass(raceclass_id)

    @callWithDatabaseWrapper
    def raceclass_attributes(self, raceclass_or_id):
        return self._racecontext.rhdata.get_raceclass_attributes(raceclass_or_id)

    @callWithDatabaseWrapper
    def raceclass_attribute_value(self, raceclass_or_id, name, default_value=None):
        for field in self._racecontext.rhui.raceclass_attributes:
            if field.name == name:
                return self._racecontext.rhdata.get_raceclass_attribute_value(raceclass_or_id, field.name, field.value)
        else:
            return self._racecontext.rhdata.get_raceclass_attribute_value(raceclass_or_id, name, default_value)

    @callWithDatabaseWrapper
    def raceclass_ids_by_attribute(self, name, value):
        return self._racecontext.rhdata.get_raceclass_id_by_attribute(name, value)

    @callWithDatabaseWrapper
    def raceclass_add(self, name=None, description=None, raceformat=None, win_condition=None, rounds=None, heat_advance_type=None, round_type=None):
        #TODO add rank settings
        data = {}

        for name, value in [
            ('name', name),
            ('description', description),
            ('format_id', raceformat),
            ('win_condition', win_condition),
            ('rounds', rounds),
            ('heat_advance_type', heat_advance_type),
            ('round_type', round_type),
            ]:
            if value is not None:
                data[name] = value

        if data:
            return self._racecontext.rhdata.add_raceClass(data)

    @callWithDatabaseWrapper
    def raceclass_duplicate(self, source_class_or_id):
        return self._racecontext.rhdata.duplicate_raceClass(source_class_or_id)

    @callWithDatabaseWrapper
    def raceclass_alter(self, raceclass_id, name=None, description=None, raceformat=None, win_condition=None, rounds=None, heat_advance_type=None, round_type=None, rank_settings=None, attributes=None):
        data = {}

        if isinstance(attributes, dict):
            data['class_id'] = raceclass_id
            for key, value in attributes.items():
                data['class_attr'] = key
                data['value'] = value
                self._racecontext.rhdata.alter_raceClass(data)

            data = {}

        for name, value in [
            ('class_name', name),
            ('class_description', description),
            ('class_format', raceformat),
            ('win_condition', win_condition),
            ('rounds', rounds),
            ('heat_advance', heat_advance_type),
            ('round_type', round_type),
            ('rank_settings', rank_settings),
            ]:
            if value is not None:
                data[name] = value

        if data:
            data['class_id'] = raceclass_id
            return self._racecontext.rhdata.alter_raceClass(data)

    @callWithDatabaseWrapper
    def raceclass_results(self, raceclass_or_id):
        return self._racecontext.rhdata.get_results_raceClass(raceclass_or_id)

    @callWithDatabaseWrapper
    def raceclass_ranking(self, raceclass_or_id):
        return self._racecontext.rhdata.get_ranking_raceClass(raceclass_or_id)

    @callWithDatabaseWrapper
    def raceclass_delete(self, raceclass_or_id):
        return self._racecontext.rhdata.delete_raceClass(raceclass_or_id)

    @callWithDatabaseWrapper
    def raceclasses_reset(self):
        return self._racecontext.rhdata.reset_raceClasses()

    # Race Format

    @property
    @callWithDatabaseWrapper
    def raceformats(self):
        return self._racecontext.rhdata.get_raceFormats()

    @callWithDatabaseWrapper
    def raceformat_by_id(self, format_id):
        return self._racecontext.rhdata.get_raceFormat(format_id)

    @callWithDatabaseWrapper
    def raceformat_add(self, name=None, unlimited_time=None, race_time_sec=None, lap_grace_sec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None):
        data = {}

        for name, value in [
            ('format_name', name),
            ('unlimited_time', unlimited_time),
            ('race_time_sec', race_time_sec),
            ('lap_grace_sec', lap_grace_sec),
            ('staging_fixed_tones', staging_fixed_tones),
            ('staging_delay_tones', staging_delay_tones),
            ('start_delay_min_ms', start_delay_min_ms),
            ('start_delay_max_ms', start_delay_max_ms),
            ('start_behavior', start_behavior),
            ('win_condition', win_condition),
            ('number_laps_win', number_laps_win),
            ('team_racing_mode', team_racing_mode),
            ('points_method', points_method),
            ]:
            if value is not None:
                data[name] = value

        return self._racecontext.rhdata.add_format(data)

    @callWithDatabaseWrapper
    def raceformat_attributes(self, raceformat_or_id):
        return self._racecontext.rhdata.get_raceformat_attributes(raceformat_or_id)

    @callWithDatabaseWrapper
    def raceformat_attribute_value(self, raceformat_or_id, name, default_value=None):
        for field in self._racecontext.rhui.raceformat_attributes:
            if field.name == name:
                return self._racecontext.rhdata.get_raceformat_attribute_value(raceformat_or_id, field.name, field.value)
        else:
            return self._racecontext.rhdata.get_raceformat_attribute_value(raceformat_or_id, name, default_value)

    @callWithDatabaseWrapper
    def raceformat_ids_by_attribute(self, name, value):
        return self._racecontext.rhdata.get_raceformat_id_by_attribute(name, value)

    @callWithDatabaseWrapper
    def raceformat_duplicate(self, source_format_or_id):
        return self._racecontext.rhdata.duplicate_raceFormat(source_format_or_id)

    @callWithDatabaseWrapper
    def raceformat_alter(self, raceformat_id, name=None, unlimited_time=None, race_time_sec=None, lap_grace_sec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None, points_settings=None, attributes=None):
        data = {}

        if isinstance(attributes, dict):
            data['format_id'] = raceformat_id
            for key, value in attributes.items():
                data['format_attr'] = key
                data['value'] = value
                self._racecontext.rhdata.alter_raceFormat(data)

            data = {}

        for name, value in [
            ('format_name', name),
            ('unlimited_time', unlimited_time),
            ('race_time_sec', race_time_sec),
            ('lap_grace_sec', lap_grace_sec),
            ('staging_fixed_tones', staging_fixed_tones),
            ('staging_delay_tones', staging_delay_tones),
            ('start_delay_min_ms', start_delay_min_ms),
            ('start_delay_max_ms', start_delay_max_ms),
            ('start_behavior', start_behavior),
            ('win_condition', win_condition),
            ('number_laps_win', number_laps_win),
            ('team_racing_mode', team_racing_mode),
            ('points_method', points_method),
            ('points_settings', points_settings),
            ]:
            if value is not None:
                data[name] = value

        if data:
            data['format_id'] = raceformat_id
            return self._racecontext.rhdata.alter_raceFormat(data)

    @callWithDatabaseWrapper
    def raceformat_delete(self, raceformat_id):
        return self._racecontext.rhdata.delete_raceFormat(raceformat_id)

    @callWithDatabaseWrapper
    def raceformats_reset(self):
        return self._racecontext.rhdata.reset_raceFormats()

    # Frequency Sets (Profiles)

    @property
    @callWithDatabaseWrapper
    def frequencysets(self):
        return self._racecontext.rhdata.get_profiles()

    @callWithDatabaseWrapper
    def frequencyset_by_id(self, set_id):
        return self._racecontext.rhdata.get_profile(set_id)

    @callWithDatabaseWrapper
    def frequencyset_add(self, name=None, description=None, frequencies=None, enter_ats=None, exit_ats=None):
        data = {}

        source_profile = self._racecontext.race.profile
        new_profile = self._racecontext.rhdata.duplicate_profile(source_profile) 

        for name, value in [
            ('profile_name', name),
            ('profile_description', description),
            ('frequencies', frequencies),
            ('enter_ats', enter_ats),
            ('exit_ats', exit_ats),
            ]:
            if value is not None:
                data[name] = value

        if data:
            data['profile_id'] = new_profile.id
            new_profile = self._racecontext.rhdata.alter_profile(data)

        return new_profile

    @callWithDatabaseWrapper
    def frequencyset_duplicate(self, source_set_or_id):
        return self._racecontext.rhdata.duplicate_profile(source_set_or_id)

    @callWithDatabaseWrapper
    def frequencyset_alter(self, set_id, name=None, description=None, frequencies=None, enter_ats=None, exit_ats=None):
        data = {}

        for name, value in [
            ('profile_name', name),
            ('profile_description', description),
            ('frequencies', frequencies),
            ('enter_ats', enter_ats),
            ('exit_ats', exit_ats),
            ]:
            if value is not None:
                data[name] = value

        if data:
            data['profile_id'] = set_id
            result = self._racecontext.rhdata.alter_profile(data)

            if set_id == self._racecontext.race.profile.id:
                self._racecontext.race.profile = result
                for idx, value in enumerate(json.loads(result.frequencies)['f']):
                    if idx < self._racecontext.race.num_nodes:
                        self._racecontext.interface.set_frequency(idx, value)
                self._racecontext.rhui.emit_frequency_data()

            return result

    @callWithDatabaseWrapper
    @callWithDatabaseWrapper
    def frequencyset_delete(self, set_or_id):
        return self._racecontext.rhdata.delete_profile(set_or_id)

    @callWithDatabaseWrapper
    def frequencysets_reset(self):
        return self._racecontext.rhdata.reset_profiles()

    # Saved Race

    @property
    @callWithDatabaseWrapper
    def races(self):
        return self._racecontext.rhdata.get_savedRaceMetas()

    @callWithDatabaseWrapper
    def race_by_id(self, race_id):
        return self._racecontext.rhdata.get_savedRaceMeta(race_id)

    @callWithDatabaseWrapper
    def race_attributes(self, race_or_id):
        return self._racecontext.rhdata.get_savedrace_attributes(race_or_id)

    @callWithDatabaseWrapper
    def race_attribute_value(self, race_or_id, name, default_value=None):
        for field in self._racecontext.rhui.savedrace_attributes:
            if field.name == name:
                return self._racecontext.rhdata.get_savedrace_attribute_value(race_or_id, field.name, field.value)
        else:
            return self._racecontext.rhdata.get_savedrace_attribute_value(race_or_id, name, default_value)

    @callWithDatabaseWrapper
    def race_ids_by_attribute(self, name, value):
        return self._racecontext.rhdata.get_savedrace_id_by_attribute(name, value)

    @callWithDatabaseWrapper
    def race_by_heat_round(self, heat_id, round_number):
        return self._racecontext.rhdata.get_savedRaceMeta_by_heat_round(heat_id, round_number)

    @callWithDatabaseWrapper
    def races_by_heat(self, heat_id):
        return self._racecontext.rhdata.get_savedRaceMetas_by_heat(heat_id)

    @callWithDatabaseWrapper
    def races_by_raceclass(self, raceclass_id):
        return self._racecontext.rhdata.get_savedRaceMetas_by_raceClass(raceclass_id)

    @callWithDatabaseWrapper
    def race_add(self, round_id, heat_id, class_id, format_id, start_time, start_time_formatted):
        data = {}

        for name, value in [
            ('round_id', round_id),
            ('heat_id', heat_id),
            ('class_id', class_id),
            ('format_id', format_id),
            ('start_time', start_time),
            ('start_time_formatted', start_time_formatted)
            ]:
            if value is not None:
                data[name] = value

        if data:
            return self._racecontext.rhdata.add_savedRaceMeta(data)

    @callWithDatabaseWrapper
    def race_alter(self, race_id, attributes=None):
        data = {}

        if isinstance(attributes, dict):
            data['race_id'] = race_id
            for key, value in attributes.items():
                data['race_attr'] = key
                data['value'] = value
                self._racecontext.rhdata.alter_savedRaceMeta(race_id, data)

    @callWithDatabaseWrapper
    def race_results(self, race_or_id):
        return self._racecontext.rhdata.get_results_savedRaceMeta(race_or_id)

    @callWithDatabaseWrapper
    def races_clear(self):
        return self._racecontext.rhdata.clear_race_data()

    # Race -> Pilot Run

    @property
    @callWithDatabaseWrapper
    def pilotruns(self):
        return self._racecontext.rhdata.get_savedPilotRaces()

    @callWithDatabaseWrapper
    def pilotrun_by_id(self, run_id):
        return self._racecontext.rhdata.get_savedPilotRace(run_id)

    @callWithDatabaseWrapper
    def pilotruns_by_race(self, race_id):
        return self._racecontext.rhdata.get_savedPilotRaces_by_savedRaceMeta(race_id)

    def pilotrun_add(self, race_id, node_index, pilot_id, history_values, history_times, enter_at, exit_at, frequency, laps):
        data = {}

        for name, value in [
            ('race_id', race_id),
            ('pilot_id', pilot_id),
            ('history_values', history_values),
            ('history_times', history_times),
            ('enter_at', enter_at),
            ('exit_at', exit_at),
            ('frequency', frequency),
            ('laps', laps),
            ]:
            if value is not None:
                data[name] = value

        if data:
            return self._racecontext.rhdata.add_race_data({node_index: data})


    # Race -> Pilot Run -> Laps

    @property
    @callWithDatabaseWrapper
    def laps(self):
        return self._racecontext.rhdata.get_savedRaceLaps()

    @callWithDatabaseWrapper
    def laps_by_pilotrun(self, run_id):
        return self._racecontext.rhdata.get_savedRaceLaps_by_savedPilotRace(run_id)

    @callWithDatabaseWrapper
    def lap_splits(self):
        return self._racecontext.rhdata.get_lapSplits()

    # Options

    @property
    @callWithDatabaseWrapper
    def options(self):
        return self._racecontext.rhdata.get_options()

    @callWithDatabaseWrapper
    def option(self, name, default=False, as_int=False):
        # Deprecation of options migrated to config
        for item in self._racecontext.serverconfig.migrations:
            if item.source == name:
                logger.warning(
                    "Deprecation: RHAPI.option called for migrated property; use config.get_item('{}', '{}')".format(
                        item.section, name),
                    stack_info=True)

                if as_int:
                    if default is not False:
                        return self._racecontext.serverconfig.get_item_int(item.section, name, default)
                    else:
                        return self._racecontext.serverconfig.get_item_int(item.section, name)

                if default is not False:
                    return self._racecontext.serverconfig.get_item(item.section, name, default)
                else:
                    return self._racecontext.serverconfig.get_item(item.section, name)


        for setting in self._racecontext.rhui.general_settings:
            if setting.name == name:
                field = setting.field
                default = field.value
                if field.field_type == UIFieldType.BASIC_INT:
                    as_int = True
                break

        if as_int:
            if default is not False:
                return self._racecontext.rhdata.get_optionInt(name, default)
            else:
                return self._racecontext.rhdata.get_optionInt(name)

        if default is not False:
            return self._racecontext.rhdata.get_option(name, default)
        else:
            return self._racecontext.rhdata.get_option(name)

    @callWithDatabaseWrapper
    def option_set(self, name, value):
        # Deprecation of options migrated to config
        for item in self._racecontext.serverconfig.migrations:
            if item.source == name:
                logger.warning(
                    "Deprecation: RHAPI.option_set called for migrated property; use config.set_item('{}', '{}')".format(
                        item.section, name),
                    stack_info=True)
                return self._racecontext.serverconfig.set_item(item.section, name, value)

        return self._racecontext.rhdata.set_option(name, value)

    @callWithDatabaseWrapper
    def options_reset(self):
        return self._racecontext.rhdata.reset_options()

    # Event

    @callWithDatabaseWrapper
    def event_results(self):
        return self._racecontext.rhdata.get_results_event()


#
# Event Results
#
class EventResultsAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def results(self):
        return self._racecontext.pagecache.get_cache()


#
# Data input/output
#
class IOAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def exporters(self):
        return self._racecontext.export_manager.exporters

    def run_export(self, exporter_id):
        return self._racecontext.export_manager.export(exporter_id)

    @property
    def importers(self):
        return self._racecontext.import_manager.importers

    def run_import(self, importer_id, data, import_args=None):
        return self._racecontext.import_manager.run_import(importer_id, data, import_args)


#
# Heat Generation
#
class HeatGenerateAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def generators(self):
        return self._racecontext.heat_generate_manager.generators

    @callWithDatabaseWrapper
    def generate(self, generator_id, generate_args):
        return self._racecontext.heat_generate_manager.generate(generator_id, generate_args)


#
# Class Ranking
#
class ClassRankAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def methods(self):
        return self._racecontext.raceclass_rank_manager.methods


#
# Points
#
class PointsAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def methods(self):
        return self._racecontext.race_points_manager.methods


#
# LED
#
class LEDAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def enabled(self):
        return self._racecontext.led_manager.isEnabled()

    @property
    def effects(self):
        return self._racecontext.led_manager.getRegisteredEffects()

    def effect_by_event(self, event):
        return self._racecontext.led_manager.getEventEffect(event)

    def effect_set(self, event, name):
        return self._racecontext.led_manager.setEventEffect(event, name)

    def clear(self):
        return self._racecontext.led_manager.clear()

    def display_color(self, seat_index, from_result=False):
        return self._racecontext.led_manager.getDisplayColor(seat_index, from_result)

    def activate_effect(self, args):
        return self._racecontext.led_manager.activateEffect(args)


#
# VRx Control
#
class VRxControlAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def enabled(self):
        return self._racecontext.vrx_manager.isEnabled()

    def kill(self):
        return self._racecontext.vrx_manager.kill()

    @property
    def status(self):
        return self._racecontext.vrx_manager.getControllerStatus()

    @property
    def devices(self):
        return self._racecontext.vrx_manager.getDevices()

    def devices_by_pilot(self, seat, pilot_id):
        return self._racecontext.vrx_manager.getActiveDevices(seat, pilot_id)


#
# Active Race
#
class RaceAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def pilots(self):
        return self._racecontext.race.node_pilots

    @property
    def teams(self):
        return self._racecontext.race.node_teams

    @property
    def slots(self):
        return self._racecontext.race.num_nodes

    @property
    def seat_colors(self):
        return self._racecontext.race.seat_colors

    def update_colors(self):
        return self._racecontext.race.updateSeatColors()

    @property
    def heat(self):
        return self._racecontext.race.current_heat

    @heat.setter
    @callWithDatabaseWrapper
    def heat(self, heat_id):
        return self._racecontext.race.set_heat(heat_id)

    @property
    def round(self):
        return self._racecontext.rhdata.get_round_num_for_heat(self._racecontext.race.current_heat)

    @property
    @callWithDatabaseWrapper
    def frequencyset(self):
        return self._racecontext.race.profile

    @frequencyset.setter
    @callWithDatabaseWrapper
    def frequencyset(self, set_id):
        self._frequencyset_set({'profile': set_id})

    @callWithDatabaseWrapper
    def _frequencyset_set(self, data):
        pass # replaced externally. TODO: Refactor management functions

    @property
    @callWithDatabaseWrapper
    def raceformat(self):
        return self._racecontext.race.format

    @raceformat.setter
    @callWithDatabaseWrapper
    def raceformat(self, format_id):
        self._raceformat_set({'race_format': format_id})

    def _raceformat_set(self, data):
        pass # replaced externally. TODO: Refactor management functions

    @property
    def status(self):
        return self._racecontext.race.race_status

    @property
    def status_message(self):
        return self._racecontext.race.status_message

    @property
    def phonetic_status_msg(self):
        return self._racecontext.race.phonetic_status_msg

    @property
    def stage_time_internal(self):
        return self._racecontext.race.stage_time_monotonic

    @property
    def start_time(self):
        return self._racecontext.race.start_time

    @property
    def start_time_internal(self):
        return self._racecontext.race.start_time_monotonic

    @property
    def end_time_internal(self):
        return self._racecontext.race.end_time

    @property
    def seats_finished(self):
        return self._racecontext.race.node_has_finished

    @property
    @callWithDatabaseWrapper
    def laps(self):
        return self._racecontext.race.get_lap_results()

    @property
    def any_laps_recorded(self):
        return self._racecontext.race.any_laps_recorded()

    @property
    def laps_raw(self):
        payload = []
        for node_idx, laps in self._racecontext.race.node_laps.items():
            if len(laps):
                laps_list = []
                for lap in laps:
                    laps_list.append(dataclasses.asdict(lap))
                payload.append(laps_list)
            else:
                payload.append([])
        return payload

    @property
    def laps_active_raw(self, filter_late_laps=False):
        payload = []
        for node_idx, laps in self._racecontext.race.get_active_laps(filter_late_laps).items():
            if len(laps):
                laps_list = []
                for lap in laps:
                    laps_list.append(dataclasses.asdict(lap))
                payload.append(laps_list)
            else:
                payload.append([])
        return payload

    def lap_add(self, seat_index, timestamp):
        seat = self._racecontext.interface.nodes[seat_index]
        return self._racecontext.race.add_lap(seat, timestamp, LapSource.API)

    @property
    @callWithDatabaseWrapper
    def results(self):
        return self._racecontext.race.get_results()

    @property
    @callWithDatabaseWrapper
    def team_results(self):
        return self._racecontext.race.get_team_results()

    @property
    @callWithDatabaseWrapper
    def coop_results(self):
        return self._racecontext.race.get_coop_results()

    @property
    def win_status(self):
        return self._racecontext.race.win_status

    @property
    def race_winner_name(self):
        return self._racecontext.race.race_winner_name

    @property
    def race_winner_phonetic(self):
        return self._racecontext.race.race_winner_phonetic

    @property
    def race_winner_lap_id(self):
        return self._racecontext.race.race_winner_lap_id

    @property
    def race_winner_pilot_id(self):
        return self._racecontext.race.race_winner_pilot_id

    @property
    def prev_race_winner_name(self):
        return self._racecontext.race.prev_race_winner_name

    @property
    def prev_race_winner_phonetic(self):
        return self._racecontext.race.prev_race_winner_phonetic

    @property
    def prev_race_winner_pilot_id(self):
        return self._racecontext.race.prev_race_winner_pilot_id

    @property
    def race_leader_lap(self):
        return self._racecontext.race.race_leader_lap

    @property
    def race_leader_pilot_id(self):
        return self._racecontext.race.race_leader_pilot_id
    
    def schedule(self, sec_or_none, minutes=0):
        return self._racecontext.race.schedule(sec_or_none, minutes)

    @property
    def scheduled(self):
        if self._racecontext.race.scheduled:
            return self._racecontext.race.scheduled_time
        else:
            return None

    def stage(self, args=None):
        return self._racecontext.race.stage(args)

    def stop(self, doSave=False):
        return self._racecontext.race.stop(doSave)

    def save(self):
        return self._racecontext.race.save()

    def clear(self):
        return self._racecontext.race.discard_laps()


#
# Language
#
class LanguageAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def languages(self):
        return self._racecontext.language.getLanguages()

    @property
    def dictionary(self):
        return self._racecontext.language.getAllLanguages()

    def __(self, text, domain=''):
        return self._racecontext.language.__(text, domain)


#
# Hardware Interface
#
class HardwareInterfaceAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def seats(self):
        return self._racecontext.interface.nodes


#
# Server Config
#
class ServerConfigAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    def register_section(self, section):
        return self._racecontext.serverconfig.register_section(section)

    @property
    def get_all(self):
        return copy.deepcopy(self._racecontext.serverconfig.config)

    def get(self, section, name, as_int=False):
        if as_int:
            return self._racecontext.serverconfig.get_item_int(section, name)
        else:
            return self._racecontext.serverconfig.get_item(section, name)

    def set(self, section, name, value):
        return self._racecontext.serverconfig.set_item(section, name, value)

    def config(self):
        # Deprecated. Retain for compatibility in v4. Changed before documented.
        return self.get_all()

    def get_item(self, section, name, as_int=False):
        # Deprecated. Retain for compatibility in v4. Was used internally but changed before documented.
        return self.get(section, name, as_int)

    def set_item(self, section, name, value):
        # Deprecated. Retain for compatibility in v4. Was used internally but changed before documented.
        return self.set(section, name, value)


#
# Sensors
#
class SensorsAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    @property
    def sensors_dict(self):
        return self._racecontext.sensors.sensors_dict

    @property
    def sensor_names(self):
        return list(self._racecontext.sensors.sensors_dict.keys())

    @property
    def sensor_objs(self):
        return list(self._racecontext.sensors.sensors_dict.values())

    def sensor_obj(self, name):
        return self._racecontext.sensors.sensors_dict[name]


#
# Events
#
class EventsAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    def on(self, event, handler_fn, default_args=None, priority=None, unique=False, name=None):
        if not priority:
            if event in [
                    Evt.ACTIONS_INITIALIZE,
                    Evt.CLASS_RANK_INITIALIZE,
                    Evt.DATA_EXPORT_INITIALIZE,
                    Evt.DATA_IMPORT_INITIALIZE,
                    Evt.HEAT_GENERATOR_INITIALIZE,
                    Evt.LED_INITIALIZE,
                    Evt.POINTS_INITIALIZE,
                    Evt.VRX_INITIALIZE,
                ]:
                priority = 75
            else:
                priority = 200

        if not name:
            name = inspect.getmodule(handler_fn).__name__

        self._racecontext.events.on(event, name, handler_fn, default_args, priority, unique)

    def off(self, event, name):
        self._racecontext.events.off(event, name)

    def trigger(self, event, args):
        self._racecontext.events.trigger(event, args)

#
# Server
#
class ServerAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    def enable_heartbeat_event(self):
        self._racecontext.serverstate.enable_heartbeat_event = True

    @property
    def info(self):
        return self._racecontext.serverstate.info_dict

    @property
    def plugins(self):
        return self._racecontext.serverstate.plugins

    @property
    def program_start_epoch_time(self):
        return self._racecontext.serverstate.program_start_epoch_time

    @property
    def program_start_mtonic(self):
        return self._racecontext.serverstate.program_start_mtonic

    @property
    def mtonic_to_epoch_millis_offset(self):
        return self._racecontext.serverstate.mtonic_to_epoch_millis_offset

    @property
    def program_start_epoch_formatted(self):
        return self._racecontext.serverstate.program_start_epoch_formatted

    @property
    def program_start_time_formatted(self):
        return self._racecontext.serverstate.program_start_time_formatted

    def monotonic_to_epoch_millis(self, secs):
        return self._racecontext.serverstate.monotonic_to_epoch_millis(secs)

    def epoch_millis_to_monotonic(self, ms):
        return self._racecontext.serverstate.epoch_millis_to_monotonic(ms)

    @property
    def seat_color_defaults(self):
        return self._racecontext.serverstate.seat_color_defaults

    @property
    def program_dir(self):
        return self._racecontext.serverstate.program_dir

    @property
    def data_dir(self):
        return self._racecontext.serverstate.data_dir

#
# Filters
#
class FilterAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    def add(self, hook, name, fn, priority=200):
        self._racecontext.filters.add_filter(hook, name, fn, priority)

    def remove(self, hook, name):
        self._racecontext.filters.remove_filter(hook, name)

    def run(self, hook, data):
        return self._racecontext.filters.run_filters(hook, data)


#
# Utility Functions
#
class UtilsAPI():
    def __init__(self, race_context):
        self._racecontext = race_context

    # Convert milliseconds to 00:00.000
    def format_time_to_str(self, millis, time_format=None):
        if not time_format:
            time_format = self._racecontext.serverconfig.get_item('UI', 'timeFormat')

        return RHUtils.format_time_to_str(millis, timeformat=time_format)

    # Convert milliseconds to 00:00.000 with leading zeros removed
    def format_split_time_to_str(self, millis, time_format=None):
        if not time_format:
            time_format = self._racecontext.serverconfig.get_item('UI', 'timeFormat')

        return RHUtils.format_time_to_str(millis, timeformat=time_format)

    # Convert milliseconds to phonetic callout string
    def format_phonetic_time_to_str(self, millis, time_format=None):
        if not time_format:
            time_format = self._racecontext.serverconfig.get_item('UI', 'timeFormat')

        return RHUtils.format_phonetic_time_to_str(millis, timeformat=time_format)

    # Generate unique name within a naming context: name, name 2..
    def generate_unique_name(self, desired_name, other_names):
        return RHUtils.uniqueName(desired_name, other_names)

    # Generate unique name within a naming context, using base only: name 1, name 2..
    def generate_unique_name_from_base(self, base_name, other_names):
        return RHUtils.unique_name_from_base(base_name, other_names)

    # Convert HSL color values to hexadecimal string
    def color_hsl_to_hexstring(self, h, s, l):
        return RHUtils.hslToHex(h, s, l)

    # Convert hexadecimal color values to packed int (LED)
    def color_hexstring_to_int(self, hex_color):
        return RHUtils.hexToColor(hex_color)

