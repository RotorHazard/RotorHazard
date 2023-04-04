#
# RHUI Helper
# Provides abstraction for user interface
#

import logging
logger = logging.getLogger(__name__)

class RHUI():
    def __init__(self):
        self.pilot_attributes = []

    def register_pilot_attribute(self, name, label, fieldtype="text"):
        self.pilot_attributes.append(PilotAttribute(name, label, fieldtype="text"))
        return True

    def get_pilot_attributes(self):
        return self.pilot_attributes

class PilotAttribute():
    def __init__(self, name, label, fieldtype="text"):
        self.name = name
        self.label = label
        self.fieldtype = fieldtype