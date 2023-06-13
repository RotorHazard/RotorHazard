''' Class to access race functions and details '''

import logging
from attr import field
logger = logging.getLogger(__name__)

class RHAPI():
    def __init__(self, RaceContext):
        self.api_version = 1

        self._racecontext = RaceContext

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
        self.eventresults = EventResultsAPI(self._racecontext)

        self.__ = self.language.__


#
# UI helpers
#
class UserInterfaceAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

    # UI Panel
    @property
    def panels(self):
        return self._racecontext.rhui.ui_panels

    def register_panel(self, name, label, page, order=0):
        return self._racecontext.rhui.register_ui_panel(name, label, page, order)

    # Quick button
    def register_quickbutton(self, panel, name, label, function):
        return self._racecontext.rhui.register_quickbutton(panel, name, label, function)

    # Blueprint
    def blueprint_add(self, blueprint):
        return self._racecontext.rhui.add_blueprint(blueprint)

    # Messaging
    def message_speak(self, text):
        self._racecontext.rhui.emit_phonetic_text(text)

    def message_notify(self, message):
        self._racecontext.rhui.emit_priority_message(message, False)

    def message_alert(self, message):
        self._racecontext.rhui.emit_priority_message(message, True)


#
# Data structures
#
class FieldsAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

    # Pilot Attribute
    @property
    def pilot_attributes(self):
        return self._racecontext.rhui.pilot_attributes

    def register_pilot_attribute(self, name, label, fieldtype="text"):
        return self._racecontext.rhui.register_pilot_attribute(name, label, fieldtype)

    # General Setting
    @property
    def options(self):
        return self._racecontext.rhui.general_settings

    def register_option(self, name, label, panel=None, fieldtype="text", order=0):
        return self._racecontext.rhui.register_general_setting(name, label, panel, fieldtype, order)


#
# Database Access
#
class DatabaseAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

    # Global

    def clear_all(self):
        return self._racecontext.rhdata.reset_all()

    # Pilot

    @property
    def pilots(self):
        return self._racecontext.rhdata.get_pilots()

    def pilot_by_id(self, pilot_id):
        return self._racecontext.rhdata.get_pilot(pilot_id)

    def pilot_attributes(self, pilot_or_id):
        return self._racecontext.rhdata.get_pilot_attributes(pilot_or_id)

    def pilot_attribute_value(self, pilot_or_id, name, default_value=None):
        return self._racecontext.rhdata.get_pilot_attribute_value(pilot_or_id, name, default_value)

    def pilot_add(self, pattern=None):
        return self._racecontext.rhdata.add_pilot(pattern)

    def pilot_alter(self, pattern):
        return self._racecontext.rhdata.alter_pilot(pattern)

    def pilot_delete(self, pilot_or_id):
        return self._racecontext.rhdata.delete_pilot(pilot_or_id)

    def pilots_clear(self):
        return self._racecontext.rhdata.clear_pilots()

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

    def heat_add(self, pattern=None):
        return self._racecontext.rhdata.add_heat(pattern)

    def heat_duplicate(self, source_heat_or_id):
        return self._racecontext.rhdata.duplicate_heat(source_heat_or_id)

    def heat_alter(self, pattern):
        return self._racecontext.rhdata.alter_heat(pattern)

    def heat_delete(self, heat_or_id):
        return self._racecontext.rhdata.delete_heat(heat_or_id)

    def heats_clear(self):
        return self._racecontext.rhdata.reset_heats()

    # Slots

    @property
    def slots(self):
        return self._racecontext.rhdata.get_heatNodes()

    def slots_by_heat(self, heat_id):
        return self._racecontext.rhdata.get_heatNodes_by_heat(heat_id)

    def slot_alter_fast(self, pattern):
        return self._racecontext.rhdata.alter_heatNodes_fast(pattern)

    # Race Class

    @property
    def raceclasses(self):
        return self._racecontext.rhdata.get_raceClasses()

    def raceclass_by_id(self, raceclass_id):
        return self._racecontext.rhdata.get_raceClass(raceclass_id)

    def raceclass_add(self, pattern=None):
        return self._racecontext.rhdata.add_raceClass(pattern)

    def raceclass_duplicate(self, source_class_or_id):
        return self._racecontext.rhdata.duplicate_raceClass(source_class_or_id)

    def raceclass_alter(self, pattern):
        return self._racecontext.rhdata.alter_raceClass(pattern)

    def raceclass_results(self, raceclass_or_id):
        return self._racecontext.rhdata.get_results_raceClass(raceclass_or_id)

    def raceclass_ranking(self, raceclass_or_id):
        return self._racecontext.rhdata.get_ranking_raceClass(raceclass_or_id)

    def raceclass_delete(self, raceclass_or_id):
        return self._racecontext.rhdata.delete_raceClass(raceclass_or_id)

    def raceclasses_clear(self):
        return self._racecontext.rhdata.reset_raceClasses()

    # Race Format

    @property
    def raceformats(self):
        return self._racecontext.rhdata.get_raceFormats()

    def raceformat_by_id(self, format_id):
        return self._racecontext.rhdata.get_raceFormat(format_id)

    def raceformat_add(self, pattern=None):
        return self._racecontext.rhdata.add_format(pattern)

    def raceformat_duplicate(self, source_format_or_id):
        return self._racecontext.rhdata.duplicate_raceFormat(source_format_or_id)

    def raceformat_alter(self, pattern):
        return self._racecontext.rhdata.alter_raceFormat(pattern)

    def raceformat_delete(self, raceformat_id):
        return self._racecontext.rhdata.delete_raceFormat(raceformat_id)

    def raceformats_clear(self):
        return self._racecontext.rhdata.clear_raceFormats()

    # Frequency Sets (Profiles)

    @property
    def frequencysets(self):
        return self._racecontext.rhdata.get_profiles()

    def frequencyset_by_id(self, set_id):
        return self._racecontext.rhdata.get_profile(set_id)

    def frequencyset_add(self, pattern=None):
        return self._racecontext.rhdata.add_profile(pattern)

    def frequencyset_duplicate(self, source_set_or_id):
        return self._racecontext.rhdata.duplicate_profile(source_set_or_id)

    def frequencyset_alter(self, pattern):
        return self._racecontext.rhdata.alter_profile(pattern)

    def frequencyset_delete(self, set_or_id):
        return self._racecontext.rhdata.delete_profile(set_or_id)

    def frequencysets_clear(self):
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

    def pilotrun_by_race(self, race_id):
        return self._racecontext.rhdata.get_savedPilotRaces_by_savedRaceMeta(race_id)

    # Race -> Pilot Run -> Laps

    @property
    def laps(self):
        return self._racecontext.rhdata.get_savedRaceLaps()

    def laps_by_pilotrun(self, run_id):
        return self._racecontext.get_savedRaceLaps_by_savedPilotRace(run_id)

    # Options

    @property
    def options(self):
        return self._racecontext.rhdata.get_options()

    def option(self, name, default=False, **kwargs):
        # keyword parameters
        # as_int: return as integer if truthy

        if kwargs.get('as_int'):
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

    def options_clear(self):
        return self._racecontext.rhdata.reset_options()

    # Event

    def event_results(self):
        return self._racecontext.rhdata.get_results_event()


#
# Data input/output
#
class EventResultsAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

    @property
    def results(self):
        return self._racecontext.pagecache.get_cache()

    def results_clear(self):
        return self._racecontext.rhdata.clear_results_all()


#
# Data input/output
#
class IOAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

    @property
    def exporters(self):
        return self._racecontext.export_manager.exporters

    def run_export(self):
        return self._racecontext.export_manager.export()

    @property
    def importers(self):
        return self._racecontext.import_manager.importers

    def run_import(self):
        return self._racecontext.import_manager.runImport()


#
# Heat Generation
#
class HeatGenerateAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

    @property
    def generators(self):
        return self._racecontext.heat_generate_manager.generators

    def run_export(self, generator_id, generate_args):
        return self._racecontext.heat_generate_manager.generate(generator_id, generate_args)


#
# Class Ranking
#
class ClassRankAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

    @property
    def methods(self):
        return self._racecontext.raceclass_rank_manager.methods


#
# Points
#
class PointsAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

    @property
    def methods(self):
        return self._racecontext.race_points_manager.methods


#
# LED
#
class LEDAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

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
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

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
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

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

    @property
    def frequencyset(self):
        return self._racecontext.race.profile

    @property
    def raceformat(self):
        return self._racecontext.race.format

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

    def schedule(self, sec_or_none, minutes=0):
        return self._racecontext.race.schedule(sec_or_none, minutes)

    @property
    def scheduled(self):
        if self._racecontext.race.scheduled:
            return self._racecontext.race.scheduled_time
        else:
            return False

    def stage(self):
        pass # replaced externally until refactored

    def stop(self, doSave=False):
        pass # replaced externally until refactored


#
# Language
#
class LanguageAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

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
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

    @property
    def nodes(self):
        return self._racecontext.interface.nodes

