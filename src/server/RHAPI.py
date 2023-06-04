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

    def get_setting(self, name, default=None):
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

    def get_pilot(self, pilot_id):
        return self._racecontext.rhdata.get_pilot(pilot_id)

    def get_heat(self, heat_id):
        return self._racecontext.rhdata.get_heat(heat_id)

    #
    # Race
    #

    @property
    def race_pilots(self):
        return self._racecontext.race.node_pilots

    @property
    def race_heat(self):
        return self._racecontext.race.current_heat

    def race_schedule(self, sec_or_none, min=0):
        return self._racecontext.race.schedule(sec_or_none, min)
