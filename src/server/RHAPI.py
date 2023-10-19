''' Class to access race functions and details '''

API_VERSION_MAJOR = 1
API_VERSION_MINOR = 0

import json
import inspect
from RHUI import UIField, UIFieldType
from eventmanager import Evt

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
        self.sensors = SensorsAPI(self._racecontext)
        self.eventresults = EventResultsAPI(self._racecontext)
        self.events = EventsAPI(self._racecontext)

        self.__ = self.language.__ # shortcut access


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

    def register_panel(self, name, label, page, order=0):
        return self._racecontext.rhui.register_ui_panel(name, label, page, order)

    # Quick button
    def register_quickbutton(self, panel, name, label, function, args=None):
        return self._racecontext.rhui.register_quickbutton(panel, name, label, function, args)

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

    # Socket
    def socket_listen(self, message, handler):
        self._racecontext.rhui.socket_listen(message, handler)

    def socket_send(self, message, data):
        self._racecontext.rhui.socket_send(message, data)

    def socket_broadcast(self, message, data):
        self._racecontext.rhui.socket_broadcast(message, data)

    # Broadcasts
    def broadcast_ui(self, page):
        self._racecontext.rhui.emit_ui(page)

    def broadcast_frequencies(self):
        self._racecontext.rhui.emit_frequency_data()

    def broadcast_pilots(self):
        self._racecontext.rhui.emit_pilot_data()

    def broadcast_heats(self):
        self._racecontext.rhui.emit_heat_data()

    def broadcast_raceclasses(self):
        self._racecontext.rhui.emit_class_data()

    def broadcast_raceformats(self):
        self._racecontext.rhui.emit_format_data()

    def broadcast_current_heat(self):
        self._racecontext.rhui.emit_current_heat()

    def broadcast_frequencyset(self):
        self._racecontext.rhui.emit_node_tuning()

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

    def reset_all(self):
        return self._racecontext.rhdata.reset_all()

    # Pilot

    @property
    def pilots(self):
        return self._racecontext.rhdata.get_pilots()

    def pilot_by_id(self, pilot_id):
        return self._racecontext.rhdata.get_pilot(pilot_id)

    def pilot_attributes(self, pilot_or_id):
        return self._racecontext.rhdata.get_pilot_attributes(pilot_or_id)

    def pilot_attribute_value(self, pilot_or_id, name):
        for field in self._racecontext.rhui.pilot_attributes:
            if field.name == name:
                return self._racecontext.rhdata.get_pilot_attribute_value(pilot_or_id, field.name, field.value)
        else:
            return self._racecontext.rhdata.get_pilot_attribute_value(pilot_or_id, name)

    def pilot_ids_by_attribute(self, name, value):
        return self._racecontext.rhdata.get_pilot_id_by_attribute(name, value)

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

    def pilot_delete(self, pilot_or_id):
        return self._racecontext.rhdata.delete_pilot(pilot_or_id)

    def pilots_reset(self):
        return self._racecontext.rhdata.reset_pilots()

    # Heat

    @property
    def heats(self):
        return self._racecontext.rhdata.get_heats()

    def heat_by_id(self, heat_id):
        return self._racecontext.rhdata.get_heat(heat_id)

    def heats_by_class(self, raceclass_id):
        return self._racecontext.rhdata.get_heats_by_class(raceclass_id)

    def heat_results(self, heat_or_id):
        return self._racecontext.rhdata.get_results_heat(heat_or_id)

    def heat_max_round(self, heat_id):
        return self._racecontext.rhdata.get_max_round(heat_id)

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

    def heat_duplicate(self, source_heat_or_id, dest_class=None):
        if dest_class:
            return self._racecontext.rhdata.duplicate_heat(source_heat_or_id, dest_class=dest_class)
        else:
            return self._racecontext.rhdata.duplicate_heat(source_heat_or_id)

    def heat_alter(self, heat_id, name=None, raceclass=None, auto_frequency=None, status=None):
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

    def heat_delete(self, heat_or_id):
        return self._racecontext.rhdata.delete_heat(heat_or_id)

    def heats_reset(self):
        return self._racecontext.rhdata.reset_heats()

    # Heat -> Slots

    @property
    def slots(self):
        return self._racecontext.rhdata.get_heatNodes()

    def slots_by_heat(self, heat_id):
        return self._racecontext.rhdata.get_heatNodes_by_heat(heat_id)

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

    def slots_alter_fast(self, slot_list):
        # !! Unsafe for general use !!
        return self._racecontext.rhdata.alter_heatNodes_fast(slot_list)

    # Race Class

    @property
    def raceclasses(self):
        return self._racecontext.rhdata.get_raceClasses()

    def raceclass_by_id(self, raceclass_id):
        return self._racecontext.rhdata.get_raceClass(raceclass_id)

    def raceclass_add(self, name=None, description=None, raceformat=None, win_condition=None, rounds=None, heat_advance_type=None):
        #TODO add rank settings
        data = {}

        for name, value in [
            ('name', name),
            ('description', description),
            ('format_id', raceformat),
            ('win_condition', win_condition),
            ('rounds', rounds),
            ('heat_advance_type', heat_advance_type),
            ]:
            if value is not None:
                data[name] = value

        if data:
            return self._racecontext.rhdata.add_raceClass(data)

    def raceclass_duplicate(self, source_class_or_id):
        return self._racecontext.rhdata.duplicate_raceClass(source_class_or_id)

    def raceclass_alter(self, raceclass_id, name=None, description=None, raceformat=None, win_condition=None, rounds=None, heat_advance_type=None, rank_settings=None):
        data = {}

        for name, value in [
            ('class_name', name),
            ('class_description', description),
            ('class_format', raceformat),
            ('win_condition', win_condition),
            ('rounds', rounds),
            ('heat_advance', heat_advance_type),
            ('rank_settings', rank_settings),
            ]:
            if value is not None:
                data[name] = value

        if data:
            data['class_id'] = raceclass_id
            return self._racecontext.rhdata.alter_raceClass(data)

    def raceclass_results(self, raceclass_or_id):
        return self._racecontext.rhdata.get_results_raceClass(raceclass_or_id)

    def raceclass_ranking(self, raceclass_or_id):
        return self._racecontext.rhdata.get_ranking_raceClass(raceclass_or_id)

    def raceclass_delete(self, raceclass_or_id):
        return self._racecontext.rhdata.delete_raceClass(raceclass_or_id)

    def raceclasses_reset(self):
        return self._racecontext.rhdata.reset_raceClasses()

    # Race Format

    @property
    def raceformats(self):
        return self._racecontext.rhdata.get_raceFormats()

    def raceformat_by_id(self, format_id):
        return self._racecontext.rhdata.get_raceFormat(format_id)

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

    def raceformat_duplicate(self, source_format_or_id):
        return self._racecontext.rhdata.duplicate_raceFormat(source_format_or_id)

    def raceformat_alter(self, raceformat_id, name=None, unlimited_time=None, race_time_sec=None, lap_grace_sec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None, points_settings=None):
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

    def raceformat_delete(self, raceformat_id):
        return self._racecontext.rhdata.delete_raceFormat(raceformat_id)

    def raceformats_reset(self):
        return self._racecontext.rhdata.reset_raceFormats()

    # Frequency Sets (Profiles)

    @property
    def frequencysets(self):
        return self._racecontext.rhdata.get_profiles()

    def frequencyset_by_id(self, set_id):
        return self._racecontext.rhdata.get_profile(set_id)

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

    def frequencyset_duplicate(self, source_set_or_id):
        return self._racecontext.rhdata.duplicate_profile(source_set_or_id)

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

    def frequencyset_delete(self, set_or_id):
        return self._racecontext.rhdata.delete_profile(set_or_id)

    def frequencysets_reset(self):
        return self._racecontext.rhdata.reset_profiles()

    # Saved Race

    @property
    def races(self):
        return self._racecontext.rhdata.get_savedRaceMetas()

    def race_by_id(self, race_id):
        return self._racecontext.rhdata.get_savedRaceMeta(race_id)

    def race_by_heat_round(self, heat_id, round_number):
        return self._racecontext.rhdata.get_savedRaceMeta_by_heat_round(heat_id, round_number)

    def races_by_heat(self, heat_id):
        return self._racecontext.rhdata.get_savedRaceMetas_by_heat(heat_id)

    def races_by_raceclass(self, raceclass_id):
        return self._racecontext.rhdata.get_savedRaceMetas_by_raceClass(raceclass_id)

    def race_results(self, race_or_id):
        return self._racecontext.rhdata.get_results_savedRaceMeta(race_or_id)

    def races_clear(self):
        return self._racecontext.rhdata.clear_race_data()

    # Race -> Pilot Run

    @property
    def pilotruns(self):
        return self._racecontext.rhdata.get_savedPilotRaces()

    def pilotrun_by_id(self, run_id):
        return self._racecontext.rhdata.get_savedPilotRace(run_id)

    def pilotruns_by_race(self, race_id):
        return self._racecontext.rhdata.get_savedPilotRaces_by_savedRaceMeta(race_id)

    # Race -> Pilot Run -> Laps

    @property
    def laps(self):
        return self._racecontext.rhdata.get_savedRaceLaps()

    def laps_by_pilotrun(self, run_id):
        return self._racecontext.rhdata.get_savedRaceLaps_by_savedPilotRace(run_id)

    def lap_splits(self):
        return self._racecontext.rhdata.get_lapSplits()

    # Options

    @property
    def options(self):
        return self._racecontext.rhdata.get_options()

    def option(self, name, default=False, as_int=False):
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

    def option_set(self, name, value):
        return self._racecontext.rhdata.set_option(name, value)

    def options_reset(self):
        return self._racecontext.rhdata.reset_options()

    # Event

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

    @property
    def heat(self):
        return self._racecontext.race.current_heat

    @heat.setter
    def heat(self, heat_id):
        self._heat_set({'heat': heat_id})

    def _heat_set(self, data):
        pass # replaced externally. TODO: Refactor management functions

    @property
    def frequencyset(self):
        return self._racecontext.race.profile

    @frequencyset.setter
    def frequencyset(self, set_id):
        self._frequencyset_set({'profile': set_id})

    def _frequencyset_set(self, data):
        pass # replaced externally. TODO: Refactor management functions

    @property
    def raceformat(self):
        return self._racecontext.race.format

    @raceformat.setter
    def raceformat(self, format_id):
        self._raceformat_set({'race_format': format_id})

    def _raceformat_set(self, data):
        pass # replaced externally. TODO: Refactor management functions

    @property
    def status(self):
        return self._racecontext.race.race_status

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
    def laps(self):
        return self._racecontext.race.get_lap_results()

    @property
    def any_laps_recorded(self):
        return self._racecontext.race.any_laps_recorded()

    @property
    def laps_raw(self):
        return self._racecontext.race.node_laps

    @property
    def laps_active_raw(self, filter_late_laps=False):
        return self._racecontext.race.get_active_laps(filter_late_laps)

    @property
    def results(self):
        return self._racecontext.race.get_results()

    @property
    def team_results(self):
        return self._racecontext.race.get_team_results()

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

    def stage(self):
        pass # replaced externally until refactored; TODO: refactor

    def stop(self, doSave=False):
        pass # replaced externally until refactored; TODO: refactor

    def save(self):
        pass # replaced externally until refactored; TODO: refactor

    def clear(self):
        pass # replaced externally until refactored; TODO: refactor


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

