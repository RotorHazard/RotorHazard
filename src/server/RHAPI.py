''' Class to access race functions and details '''

import logging
logger = logging.getLogger(__name__)

class RHAPI():
    def __init__(self, RaceContext):
        self._racecontext = RaceContext

    # Pilot Attributes
    def register_pilot_attribute(self, name, label, fieldtype="text"):
        return self._racecontext.rhui.register_pilot_attribute(name, label, fieldtype)

    @property
    def pilot_attributes(self):
        return self._racecontext.rhui.pilot_attributes

    # UI Panels
    def register_ui_panel(self, name, label, page, order=0):
        return self._racecontext.rhui.register_ui_panel(name, label, page, order)

    @property
    def ui_panels(self):
        return self._racecontext.rhui.ui_panels

    # General Settings
    def register_general_setting(self, name, label, panel=None, fieldtype="text", order=0):
        return self._racecontext.rhui.register_general_setting(name, label, panel, fieldtype, order)

    # Quick button
    def register_quickbutton(self, panel, name, label, function):
        return self._racecontext.rhui.register_quickbutton(panel, name, label, function)

    @property
    def general_settings(self):
        return self._racecontext.rhui.general_settings

    def setting(self, name, default=None):
        return self._racecontext.rhdata.get_option(name, default)

    # Blueprints
    def add_blueprint(self, blueprint):
        return self._racecontext.rhui.add_blueprint(blueprint)

    # emit frontend messages
    def emit_phonetic_text(self, text):
        self._racecontext.rhui.emit_phonetic_text(text)

    def emit_priority_message(self, message, interrupt=False):
        self._racecontext.rhui.emit_priority_message(message, interrupt)

    #
    # RHData
    #

    def pilot_by_id(self, pilot_id):
        return self._racecontext.rhdata.get_pilot(pilot_id)

    @property
    def pilots(self):
        return self._racecontext.rhdata.get_pilots()

    def heat_by_id(self, heat_id):
        return self._racecontext.rhdata.get_heat(heat_id)

    @property
    def heats(self):
        return self._racecontext.rhdata.get_heats()

    def heats_by_class(self, race_class_id):
        return self.rhdata.get_heats_by_class(race_class_id)

    def heat_results(self, heat):
        return self.rhdata.get_results_heat(heat)

    def raceclass_by_id(self, raceclass_id):
        return self._racecontext.rhdata.get_raceClass(raceclass_id)

    @property
    def raceclasses(self):
        return self._racecontext.rhdata.get_raceClasses()

    def raceclass_results(self, raceclass):
        return self._racecontext.rhdata.get_results_raceClass(raceclass)

    def raceformat_by_id(self, format_id):
        return self._racecontext.rhdata.get_raceFormat(format_id)

    def saved_race_results(self, race):
        return self.rhdata.get_results_savedRaceMeta(race)
    
    def saved_races_by_heat(self, heat_id):
        return self.rhdata.get_savedRaceMetas_by_heat(heat_id)

    #
    # Race
    #

    @property
    def race_pilots(self):
        return self._racecontext.race.node_pilots

    @property
    def race_heat(self):
        return self._racecontext.race.current_heat

    def race_schedule(self, sec_or_none, minutes=0):
        return self._racecontext.race.schedule(sec_or_none, minutes)

    def race_stage(self):
        pass #replaced externally

    def race_stop(self, doSave=False):
        pass #replaced externally

