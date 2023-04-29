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

    @property
    def general_settings(self):
        return self._racecontext.rhui.general_settings

    def get_setting(self, name, default=None):
        return self._racecontext.rhdata.get_option(name, default)

    # emit frontend messages
    def emit_priority_message(self, message, interrupt=False):
        self._racecontext.rhui.emit_priority_message(message, interrupt)
