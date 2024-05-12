''' Class to access race functions and details '''
import functools
from Database import LapSource

API_VERSION_MAJOR = 1
API_VERSION_MINOR = 1

import json
import inspect
import copy
import logging
from RHUI import UIField, UIFieldType
from eventmanager import Evt

logger = logging.getLogger(__name__)

from FlaskAppObj import APP
if APP:
    APP.app_context().push()

class RHAPI():
    """An object providing a wide range of properties and methods across RotorHazard's internal systems

    :param race_context: A handle to the :class:`RaceContext`
    :type race_context: RaceContext
    """

    def __init__(self, race_context):
        self.API_VERSION_MAJOR:int = API_VERSION_MAJOR
        """API major version"""
        self.API_VERSION_MINOR:int = API_VERSION_MINOR
        """API minor version"""
        self.server_info = None

        self._racecontext = race_context

        self.ui:UserInterfaceAPI = UserInterfaceAPI(self._racecontext)
        """A handle for an instance of :class:`UserInterfaceAPI`"""
        self.fields:FieldsAPI = FieldsAPI(self._racecontext)
        """A handle for an instance of :class:`FieldsAPI`"""
        self.db:DatabaseAPI = DatabaseAPI(self._racecontext)
        """A handle for an instance of :class:`DatabaseAPI`"""
        self.io:IOAPI = IOAPI(self._racecontext)
        """A handle for an instance of :class:`IOAPI`"""
        self.heatgen:HeatGenerateAPI = HeatGenerateAPI(self._racecontext)
        """A handle for an instance of :class:`HeatGenerateAPI`"""
        self.classrank:ClassRankAPI = ClassRankAPI(self._racecontext)
        """A handle for an instance of :class:`ClassRankAPI`"""
        self.points:PointsAPI = PointsAPI(self._racecontext)
        """A handle for an instance of :class:`PointsAPI`"""
        self.led:LEDAPI = LEDAPI(self._racecontext)
        """A handle for an instance of :class:`LEDAPI`"""
        self.vrxcontrol:VRxControlAPI = VRxControlAPI(self._racecontext)
        """A handle for an instance of :class:`VRxControlAPI`"""
        self.race:RaceAPI = RaceAPI(self._racecontext)
        """A handle for an instance of :class:`RaceAPI`"""
        self.language:LanguageAPI = LanguageAPI(self._racecontext)
        """A handle for an instance of :class:`LanguageAPI`"""
        self.interface:HardwareInterfaceAPI = HardwareInterfaceAPI(self._racecontext)
        """A handle for an instance of :class:`HardwareInterfaceAPI`"""
        self.config:ServerConfigAPI = ServerConfigAPI(self._racecontext)
        """A handle for an instance of :class:`ServerConfigAPI`"""
        self.sensors:SensorsAPI = SensorsAPI(self._racecontext)
        """A handle for an instance of :class:`SensorsAPI`"""
        self.eventresults:EventResultsAPI = EventResultsAPI(self._racecontext)
        """A handle for an instance of :class:`EventResultsAPI`"""
        self.events:EventsAPI = EventsAPI(self._racecontext)
        """A handle for an instance of :class:`EventsAPI`"""
        self.__:function = self.language.__ # shortcut access
        """A shortcut handle for :meth:`LanguageAPI.__`"""

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
    """Interact with RotorHazard's frontend user interface. These methods are accessed via :attr:`RHAPI.RHAPI.ui`
    """

    def __init__(self, race_context):
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext`
        :type race_context: :class:`RaceContext`
        """ 
        self._racecontext = race_context

    # UI Panel
    @property
    def panels(self):
        """The list of registered panels

        :return: A list of the discovered :class:`UIPanel` objects
        :rtype: list[UIPanel]
        """
        return self._racecontext.rhui.ui_panels

    def register_panel(self, name, label, page, order=0):
        """The list of registered panels

        :param name: Internal identifier for this panel
        :type name: str
        :param label: Text used as visible panel header
        :type label: str
        :param page: Page to add panel to; one of "format", "settings"
        :type page: str
        :param order: Not yet implemented, defaults to 0
        :type order: int, optional

        :return: Returns all panels
        :rtype: list[UIPanel]
        """
        return self._racecontext.rhui.register_ui_panel(name, label, page, order)

    # Quick button
    def register_quickbutton(self, panel, name, label, function, args=None):
        """Provides a simple interface to add a UI button and bind it to a function. Quickbuttons appear on assigned UI panels.

        :param panel: name of panel where button will appear
        :type panel: str
        :param name: Internal identifier for this quickbutton
        :type name: str
        :param label: Text used for visible button label
        :type label: str
        :param function: Function to run when button is pressed
        :type function: function
        :param args: Argument passed to function when called, defaults to None
        :type args: any, optional

        :return: _description_
        :rtype: _type_
        """
        return self._racecontext.rhui.register_quickbutton(panel, name, label, function, args)

    # Blueprint
    def blueprint_add(self, blueprint):
        """Add custom pages to RotorHazard's frontend with Flask Blueprints.

        :param blueprint: _description_
        :type blueprint: Blueprint
        """
        self._racecontext.rhui.add_blueprint(blueprint)

    # Messaging
    def message_speak(self, message):
        """Send a message which is parsed by the text-to-speech synthesizer.

        :param message: Text of message to be spoken
        :type message: str
        """
        self._racecontext.rhui.emit_phonetic_text(message)

    def message_notify(self, message):
        """Send a message which appears in the message center and notification bar.

        :param message: Text of message to display
        :type message: str
        """
        self._racecontext.rhui.emit_priority_message(message, False)

    def message_alert(self, message):
        """Send a message which appears as a pop-up alert.

        :param message: Text of message to display
        :type message: str
        """
        self._racecontext.rhui.emit_priority_message(message, True)

    def clear_messages(self):
        """_summary_
        """
        self._racecontext.rhui.emit_clear_priority_messages()

    # Socket
    def socket_listen(self, message, handler):
        """Calls function when a socket event is received.

        :param message: Socket event name
        :type message: str
        :param handler: Function to call
        :type handler: function
        """
        self._racecontext.rhui.socket_listen(message, handler)

    def socket_send(self, message, data):
        """_summary_

        :param message: _description_
        :type message: _type_
        :param data: _description_
        :type data: _type_
        """
        self._racecontext.rhui.socket_send(message, data)

    def socket_broadcast(self, message, data):
        """_summary_

        :param message: _description_
        :type message: _type_
        :param data: _description_
        :type data: _type_
        """
        self._racecontext.rhui.socket_broadcast(message, data)

    # Broadcasts
    @callWithDatabaseWrapper
    def broadcast_ui(self, page):
        """Broadcast UI panel setup to all connected clients.

        :param page: Page to update
        :type page: str
        """
        self._racecontext.rhui.emit_ui(page)

    @callWithDatabaseWrapper
    def broadcast_frequencies(self):
        """Broadcast seat frequencies to all connected clients.
        """
        self._racecontext.rhui.emit_frequency_data()

    @callWithDatabaseWrapper
    def broadcast_pilots(self):
        """Broadcast pilot data to all connected clients.
        """
        self._racecontext.rhui.emit_pilot_data()

    @callWithDatabaseWrapper
    def broadcast_heats(self):
        """Broadcast heat data to all connected clients.
        """
        self._racecontext.rhui.emit_heat_data()

    @callWithDatabaseWrapper
    def broadcast_raceclasses(self):
        """Broadcast race class data to all connected clients.
        """
        self._racecontext.rhui.emit_class_data()

    @callWithDatabaseWrapper
    def broadcast_raceformats(self):
        """Broadcast race format data to all connected clients.
        """
        self._racecontext.rhui.emit_format_data()

    @callWithDatabaseWrapper
    def broadcast_current_heat(self):
        """Broadcast current heat selection to all connected clients.
        """
        self._racecontext.rhui.emit_current_heat()

    @callWithDatabaseWrapper
    def broadcast_frequencyset(self):
        """Broadcast frequency set data to all connected clients.
        """
        self._racecontext.rhui.emit_node_tuning()

    @callWithDatabaseWrapper
    def broadcast_race_status(self):
        """Broadcast race setup and status to all connected clients.
        """
        self._racecontext.rhui.emit_race_status()


#
# Data structures
#
class FieldsAPI():
    """Create and access new data structures. These methods are accessed via :attr:`RHAPI.RHAPI.fields`
    """
    def __init__(self, race_context):
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
        self._racecontext = race_context

    # Pilot Attribute
    @property
    def pilot_attributes(self):
        """Provides a list of registered pilot attributes

        :return: List of pilot attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.pilot_attributes

    def register_pilot_attribute(self, field:UIField):
        """Register a pilot attribute to be displayed in the UI or otherwise made accessible to plugins.

        :param field: :class:`UIField` to register
        :type field: UIField
        :return: List of Attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.register_pilot_attribute(field)

    # Heat Attribute
    @property
    def heat_attributes(self):
        """Provides a list of registered heat attributes.

        :return: List of heat attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.heat_attributes

    def register_heat_attribute(self, field:UIField):
        """Register a heat attribute to be made accessible to plugins.

        :param field: :class:`UIField` to register
        :type field: UIField
        :return: List of Attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.register_heat_attribute(field)

    # Race Class Attribute
    @property
    def raceclass_attributes(self):
        """Provides a list of registered race class attributes.

        :return: List of race class attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.raceclass_attributes

    def register_raceclass_attribute(self, field:UIField):
        """Register a race class attribute to be made accessible to plugins.

        :param field: :class:`UIField` to register
        :type field: UIField
        :return: List of Attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.register_raceclass_attribute(field)

    # Race Attribute
    @property
    def race_attributes(self):
        """Provides a list of registered race attributes.

        :return: List of race attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.savedrace_attributes

    def register_race_attribute(self, field:UIField):
        """Register a race attribute to be made accessible to plugins.

        :param field: :class:`UIField` to register
        :type field: UIField
        :return: List of Attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.register_savedrace_attribute(field)

    # Race Attribute
    @property
    def raceformat_attributes(self):
        """Provides a list of registered race format attributes.

        :return: List of race format attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.raceformat_attributes

    def register_raceformat_attribute(self, field:UIField):
        """Register a race format attribute to be made accessible to plugins.

        :param field: :class:`UIField` to register
        :type field: UIField
        :return: List of Attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.register_raceformat_attribute(field)

    # General Setting
    @property
    def options(self):
        """Provides a list of registered options.

        :return: List of options
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.general_settings

    def register_option(self, field:UIField, panel=None, order=0):
        """Register a option to be made accessible to plugins.

        :param field: :class:`UIField` to register
        :type field: UIField
        :param panel: name of panel previously registered with ui.register_panel
        :type panel: str
        :param field: Attribute to register
        :type field: int
        :return: List of Attributes
        :rtype: list[UIField]
        """
        return self._racecontext.rhui.register_general_setting(field, panel, order)


#
# Database Access
#
class DatabaseAPI():
    def __init__(self, race_context):
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
        self._racecontext = race_context

    # Global

    @callWithDatabaseWrapper
    def reset_all(self):
        """Resets database to default state.

        :return: Database successfully reset 
        :rtype: bool
        """
        return self._racecontext.rhdata.reset_all()

    # Pilot

    @property
    @callWithDatabaseWrapper
    def pilots(self):
        """Gets all pilot records

        :return: Pilot records
        :rtype: list[Pilot]
        """
        return self._racecontext.rhdata.get_pilots()

    @callWithDatabaseWrapper
    def pilot_by_id(self, pilot_id):
        """A single pilot record. Does not include custom attributes.

        :param pilot_id: ID of pilot record to retrieve
        :type pilot_id: int
        :return: created pilot record
        :rtype: Pilot
        """
        return self._racecontext.rhdata.get_pilot(pilot_id)

    @callWithDatabaseWrapper
    def pilot_attributes(self, pilot_or_id):
        """All custom attributes assigned to pilot.

        :param pilot_or_id: Either the pilot object or the ID of pilot
        :type pilot_or_id: Pilot|int
        :return: A pilot's attributes
        :rtype: list[PilotAttribute]
        """
        return self._racecontext.rhdata.get_pilot_attributes(pilot_or_id)

    @callWithDatabaseWrapper
    def pilot_attribute_value(self, pilot_or_id, name, default_value=None):
        """The value of a single custom attribute assigned to pilot

        :param pilot_or_id: Either the pilot object or the ID of pilot
        :type pilot_or_id: Pilot|int
        :param name: Attribute to match
        :type name: str
        :param default_value: value to return if attribute is not registered (uses registered default if available), defaults to None
        :type default_value: any, optional
        :return: A :class:`PilotAttribute`
        :rtype: PilotAttribute
        """
        for field in self._racecontext.rhui.pilot_attributes:
            if field.name == name:
                return self._racecontext.rhdata.get_pilot_attribute_value(pilot_or_id, field.name, field.value)
        else:
            return self._racecontext.rhdata.get_pilot_attribute_value(pilot_or_id, name, default_value)

    @callWithDatabaseWrapper
    def pilot_ids_by_attribute(self, name, value):
        """ID of pilots with attribute matching the specified attribute/value combination

        :param name: Attribute to match
        :type name: str
        :param value: Value to match
        :type value: str
        :return: Pilots' IDs
        :rtype: list[int]
        """
        return self._racecontext.rhdata.get_pilot_id_by_attribute(name, value)

    @callWithDatabaseWrapper
    def pilot_add(self, name=None, callsign=None, phonetic=None, team=None, color=None):
        """Add a new pilot to the database.

        :param name: Name for new pilot, defaults to None
        :type name: str, optional
        :param callsign: Callsign for new pilot, defaults to None
        :type callsign: str, optional
        :param phonetic: Phonetic spelling for new pilot callsign, defaults to None
        :type phonetic: str, optional
        :param team: Team for new pilot, defaults to None
        :type team: str, optional
        :param color: Color for new pilot, defaults to None
        :type color: str, optional
        :return: Created :class:`Pilot`
        :rtype: Pilot
        """
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
        """Alter pilot data

        :param pilot_id: ID of pilot to alter
        :type pilot_id: int
        :param name: New name for pilot, defaults to None
        :type name: str, optional
        :param callsign: New callsign for pilot, defaults to None
        :type callsign: str, optional
        :param phonetic: New phonetic spelling of callsign for pilot, defaults to None
        :type phonetic: str, optional
        :param team: New team for pilot, defaults to None
        :type team: str, optional
        :param color: New color for pilot, defaults to None
        :type color: str, optional
        :param attributes: Attributes to alter, attribute values assigned to respective keys, defaults to None
        :type attributes: dict, optional
        :return: Altered :class:`Pilot`
        :rtype: Pilot
        """
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
        """Delete pilot record. Fails if pilot is associated with saved race.

        :param pilot_or_id: ID of pilot to delete
        :type pilot_or_id: int
        :return: Delete success status.
        :rtype: bool
        """
        return self._racecontext.rhdata.delete_pilot(pilot_or_id)

    @callWithDatabaseWrapper
    def pilots_reset(self):
        """Delete all pilot records.

        :return: Reset status
        :rtype: bool
        """
        return self._racecontext.rhdata.reset_pilots()

    # Heat

    @property
    @callWithDatabaseWrapper
    def heats(self):
        """Gets all heat records.

        :return: List of :class:`Heat`
        :rtype: list[Heat]
        """
        return self._racecontext.rhdata.get_heats()

    @callWithDatabaseWrapper
    def heat_by_id(self, heat_id):
        """A single heat record.

        :param heat_id: ID of heat record to retrieve
        :type heat_id: int
        :return: heat record
        :rtype: Heat
        """
        return self._racecontext.rhdata.get_heat(heat_id)

    @callWithDatabaseWrapper
    def heat_attributes(self, heat_or_id):
        """All custom attributes assigned to heat.

        :param heat_or_id: Either the heat object or the ID of heat
        :type heat_or_id: Heat|int
        :return: Heat's attributes
        :rtype: list[HeatAttribute]
        """
        return self._racecontext.rhdata.get_heat_attributes(heat_or_id)

    @callWithDatabaseWrapper
    def heat_attribute_value(self, heat_or_id, name, default_value=None):
        """The value of a single custom attribute assigned to heat.

        :param heat_or_id: Either the heat object or the ID of heat
        :type heat_or_id: Heat|int
        :param name: Attribute to retrieve
        :type name: str
        :param default_value: value to return if attribute is not registered (uses registered default if available), defaults to None
        :type default_value: any, optional
        :return: heat attribute value
        :rtype: str
        """
        for field in self._racecontext.rhui.heat_attributes:
            if field.name == name:
                return self._racecontext.rhdata.get_heat_attribute_value(heat_or_id, field.name, field.value)
        else:
            return self._racecontext.rhdata.get_heat_attribute_value(heat_or_id, name, default_value)

    @callWithDatabaseWrapper
    def heat_ids_by_attribute(self, name, value):
        """ID of heats with attribute matching the specified attribute/value combination.

        :param name: Name for new heat
        :type name: str, optional
        :param value: Raceclass ID for new heat
        :type value: int, optional
        :return: List of heat IDs
        :rtype: list[int]
        """
        return self._racecontext.rhdata.get_heat_id_by_attribute(name, value)

    @callWithDatabaseWrapper
    def heats_by_class(self, raceclass_id):
        """All heat records associated with a specific class.

        :param raceclass_id: ID of raceclass used to retrieve heats
        :type raceclass_id: int
        :return: List of heats
        :rtype: list[Heat]
        """
        return self._racecontext.rhdata.get_heats_by_class(raceclass_id)

    @callWithDatabaseWrapper
    def heat_results(self, heat_or_id):
        """The calculated summary result set for all races associated with this heat.

        :param heat_or_id: Either the heat object or the ID of heat
        :type heat_or_id: Heat|int
        :return: heat results
        :rtype: dict
        """
        return self._racecontext.rhdata.get_results_heat(heat_or_id)

    @callWithDatabaseWrapper
    def heat_max_round(self, heat_id):
        """The highest-numbered race round recorded for selected heat.

        :param heat_id: ID of heat
        :type heat_id: int
        :return: Round number
        :rtype: int
        """
        return self._racecontext.rhdata.get_max_round(heat_id)

    @callWithDatabaseWrapper
    def heat_add(self, name=None, raceclass=None, auto_frequency=None):
        """Add a new heat to the database.

        :param name: Name for new heat, defaults to None
        :type name: string, optional
        :param raceclass: Raceclass ID for new heat, defaults to None
        :type raceclass: int, optional
        :param auto_frequency: Whether to enable auto-frequency, defaults to None
        :type auto_frequency: bool, optional
        :return: The new :class:`Heat`
        :rtype: Heat
        """
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
        """Duplicate a heat record.

        :param source_heat_or_id: Either the heat object or the ID of heat to copy from
        :type source_heat_or_id: Heat|int
        :param dest_class: Raceclass ID to copy heat into, defaults to None
        :type dest_class: int, optional
        :return: The new :class:`Heat`
        :rtype: Heat
        """
        if dest_class:
            return self._racecontext.rhdata.duplicate_heat(source_heat_or_id, dest_class=dest_class)
        else:
            return self._racecontext.rhdata.duplicate_heat(source_heat_or_id)

    @callWithDatabaseWrapper
    def heat_alter(self, heat_id, name=None, raceclass=None, auto_frequency=None, status=None, attributes=None):
        """Alter heat data.

        :param heat_id: ID of heat to alter
        :type heat_id: int
        :param name: New name for heat, defaults to None
        :type name: str, optional
        :param raceclass: New raceclass ID for heat, defaults to None
        :type raceclass: int, optional
        :param auto_frequency: New auto-frequency setting for heat, defaults to None
        :type auto_frequency: bool, optional
        :param status: New status for heat, defaults to None
        :type status: HeatStatus, optional
        :param attributes: Attributes to alter, attribute values assigned to respective keys, defaults to None
        :type attributes: dict, optional
        :return: Returns tuple of this Heat and affected races
        :rtype: list[SavedRace]
        """
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
        """Delete heat. Fails if heat has saved races associated or if there is only one heat left in the database.

        :param heat_or_id: ID of heat to delete
        :type heat_or_id: Heat|int
        :return: Success status
        :rtype: bool
        """
        return self._racecontext.rhdata.delete_heat(heat_or_id)

    @callWithDatabaseWrapper
    def heats_reset(self):
        """Delete all heat records
        """
        self._racecontext.rhdata.reset_heats()

    # Heat -> Slots

    @property
    @callWithDatabaseWrapper
    def slots(self):
        """All slot records.

        :return: List of HeatNode
        :rtype: list[HeatNode]
        """
        return self._racecontext.rhdata.get_heatNodes()

    @callWithDatabaseWrapper
    def slots_by_heat(self, heat_id):
        """Slot records associated with a specific heat.

        :param heat_id: ID of heat used to retrieve slots
        :type heat_id: int
        :return: List of HeatNode
        :rtype: list[HeatNode]
        """
        return self._racecontext.rhdata.get_heatNodes_by_heat(heat_id)

    @callWithDatabaseWrapper
    def slot_alter(self, slot_id, method=None, pilot=None, seed_heat_id=None, seed_raceclass_id=None, seed_rank=None):
        """Alter slot data.

        :param slot_id: ID of slot to alter
        :type slot_id: int
        :param method: New seeding method for slot, defaults to None
        :type method: ProgramMethod, optional
        :param pilot: New ID of pilot assigned to slot, defaults to None
        :type pilot: int, optional
        :param seed_heat_id: New heat ID to use for seeding, defaults to None
        :type seed_heat_id: int, optional
        :param seed_raceclass_id: New raceclass ID to use for seeding, defaults to None
        :type seed_raceclass_id: int, optional
        :param seed_rank: New rank value to use for seeding, defaults to None
        :type seed_rank: int, optional
        :return: Affected races
        :rtype: list[SavedRace]

        With method set to ProgramMethod.NONE, most other fields are ignored. Only use seed_heat_id with ProgramMethod.HEAT_RESULT, and seed_raceclass_id with ProgramMethod.CLASS_RESULT, otherwise the assignment is ignored.
        """
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
        """Make many alterations to slots in a single database transaction as quickly as possible. Use with caution. May accept invalid input. Does not trigger events, clear associated results, or update cached data. These operations must be done manually if required.

        Input dict parameters match the parameters used in :meth:`DatabaseAPI.slot_alter` 

        :param slot_list: List of dicts containing parameters for each slot
        :type slot_list: list[dict]
        """
        # !! Unsafe for general use !!
        self._racecontext.rhdata.alter_heatNodes_fast(slot_list)

    # Race Class

    @property
    @callWithDatabaseWrapper
    def raceclasses(self):
        """All race class records.

        :return: System race classes
        :rtype: list[RaceClass]
        """
        return self._racecontext.rhdata.get_raceClasses()

    @callWithDatabaseWrapper
    def raceclass_by_id(self, raceclass_id):
        """A single race class record.

        :param raceclass_id: ID of race class record to retrieve
        :type raceclass_id: int
        :return: The race class
        :rtype: RaceClass
        """
        return self._racecontext.rhdata.get_raceClass(raceclass_id)

    @callWithDatabaseWrapper
    def raceclass_attributes(self, raceclass_or_id):
        """All custom attributes assigned to race class.

        :param raceclass_or_id: Either the race class object or the ID of race class
        :type raceclass_or_id: Raceclass|int
        :return: The class's race class attributes
        :rtype: list[RaceClassAttribute]
        """
        return self._racecontext.rhdata.get_raceclass_attributes(raceclass_or_id)

    @callWithDatabaseWrapper
    def raceclass_attribute_value(self, raceclass_or_id, name, default_value=None):
        """The value of a single custom attribute assigned to race class.

        :param raceclass_or_id: Either the race class object or the ID of race class
        :type raceclass_or_id: Raceclass|int
        :param name: Attribute to retrieve
        :type name: str
        :param default_value: Value to return if attribute is not registered (uses registered default if available), defaults to None
        :type default_value: any, optional
        :return: Attribute value as a string
        :rtype: str
        """
        for field in self._racecontext.rhui.raceclass_attributes:
            if field.name == name:
                return self._racecontext.rhdata.get_raceclass_attribute_value(raceclass_or_id, field.name, field.value)
        else:
            return self._racecontext.rhdata.get_raceclass_attribute_value(raceclass_or_id, name, default_value)

    @callWithDatabaseWrapper
    def raceclass_ids_by_attribute(self, name, value):
        """ID of race classes with attribute matching the specified attribute/value combination.

        :param name: Attribute to match
        :type name: str
        :param value: Value to match
        :type value: str
        :return: List of pilots
        :rtype: list[int]
        """
        return self._racecontext.rhdata.get_raceclass_id_by_attribute(name, value)

    @callWithDatabaseWrapper
    def raceclass_add(self, name=None, description=None, raceformat=None, win_condition=None, rounds=None, heat_advance_type=None):
        """Add a new race class to the database.

        :param name: Name for new race class, defaults to None
        :type name: str, optional
        :param description: Description for new race class, defaults to None
        :type description: str, optional
        :param raceformat: ID of format to assign, defaults to None
        :type raceformat: int, optional
        :param win_condition: Class ranking identifier to assign, defaults to None
        :type win_condition: str, optional
        :param rounds: Number of rounds to assign to race class, defaults to None
        :type rounds: int, optional
        :param heat_advance_type: Advancement method to assign to race class, defaults to None
        :type heat_advance_type: HeatAdvanceType, optional
        :return: The created :class:`RaceClass`
        :rtype: RaceClass
        """
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

    @callWithDatabaseWrapper
    def raceclass_duplicate(self, source_class_or_id):
        """Duplicate a race class.

        :param source_class_or_id: Either a race class object or the ID of a race class
        :type source_class_or_id: RaceClass|int
        :return: The created :class:`RaceClass`
        :rtype: RaceClass
        """
        return self._racecontext.rhdata.duplicate_raceClass(source_class_or_id)

    @callWithDatabaseWrapper
    def raceclass_alter(self, raceclass_id, name=None, description=None, raceformat=None, win_condition=None, rounds=None, heat_advance_type=None, rank_settings=None, attributes=None):
        """Alter race class data.

        :param raceclass_id: ID of race class to alter
        :type raceclass_id: int
        :param name: Name for new race class, defaults to None
        :type name: str, optional
        :param description: Description for new race class, defaults to None
        :type description: str, optional
        :param raceformat: ID of format to assign, defaults to None
        :type raceformat: int, optional
        :param win_condition: Class ranking identifier to assign, defaults to None
        :type win_condition: str, optional
        :param rounds: Number of rounds to assign to race class, defaults to None
        :type rounds: int, optional
        :param heat_advance_type: Advancement method to assign to race class, defaults to None
        :type heat_advance_type: HeatAdvanceType, optional
        :param rank_settings: Arguments to pass to class ranking, defaults to None
        :type rank_settings: dict, optional
        :param attributes: Attributes to alter, attribute values assigned to respective keys, defaults to None
        :type attributes: dict, optional
        :return: Returns tuple of this :class:`RaceClass` and affected races
        :rtype: list[SavedRace]
        """
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
            ('rank_settings', rank_settings),
            ]:
            if value is not None:
                data[name] = value

        if data:
            data['class_id'] = raceclass_id
            return self._racecontext.rhdata.alter_raceClass(data)

    @callWithDatabaseWrapper
    def raceclass_results(self, raceclass_or_id):
        """The calculated summary result set for all races associated with this race class.

        :param raceclass_or_id: Either the race class object or the ID of race class
        :type raceclass_or_id: RaceClass|int
        :return: Results for race class
        :rtype: dict
        """
        return self._racecontext.rhdata.get_results_raceClass(raceclass_or_id)

    @callWithDatabaseWrapper
    def raceclass_ranking(self, raceclass_or_id):
        """The calculated ranking associated with this race class.

        :param raceclass_or_id: Either the race class object or the ID of race class
        :type raceclass_or_id: RaceClass
        :return: Rankings for race class
        :rtype: dict
        """
        return self._racecontext.rhdata.get_ranking_raceClass(raceclass_or_id)

    @callWithDatabaseWrapper
    def raceclass_delete(self, raceclass_or_id):
        """Delete race class. Fails if race class has saved races associated.

        :param raceclass_or_id: Either the race class object or the ID of race class
        :type raceclass_or_id: RaceClass|int
        :return: Success status
        :rtype: bool
        """
        return self._racecontext.rhdata.delete_raceClass(raceclass_or_id)

    @callWithDatabaseWrapper
    def raceclasses_reset(self):
        """Delete all race classes.
        """
        self._racecontext.rhdata.reset_raceClasses()

    # Race Format

    @property
    @callWithDatabaseWrapper
    def raceformats(self):
        """All race formats.

        :return: System race formats
        :rtype: list[RaceFormat]
        """
        return self._racecontext.rhdata.get_raceFormats()

    @callWithDatabaseWrapper
    def raceformat_by_id(self, format_id):
        """A single race format record.

        :param format_id: ID of race format record to retrieve
        :type format_id: int
        :return: The race format
        :rtype: RaceFormat
        """
        return self._racecontext.rhdata.get_raceFormat(format_id)

    @callWithDatabaseWrapper
    def raceformat_add(self, name=None, unlimited_time=None, race_time_sec=None, lap_grace_sec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None):
        """Add a new race format to the database.

        :param name: Name for new race format, defaults to None
        :type name: str, optional
        :param unlimited_time: Unlimited Time setting for new race format, defaults to None
        :type unlimited_time: int, optional
        :param race_time_sec: Race duration for new race format, defaults to None
        :type race_time_sec: int, optional
        :param lap_grace_sec: Grace period for new race format, defaults to None
        :type lap_grace_sec: int, optional
        :param staging_fixed_tones: Fixed tones for new race forma, defaults to None
        :type staging_fixed_tones: int, optional
        :param staging_delay_tones: Delay tones setting for new race format, defaults to None
        :type staging_delay_tones: int, optional
        :param start_delay_min_ms: Delay minimum for new race format, defaults to None
        :type start_delay_min_ms: int, optional
        :param start_delay_max_ms: Maximum delay duration for new race format, defaults to None
        :type start_delay_max_ms: int, optional
        :param start_behavior: First crossing behavior for new race format, defaults to None
        :type start_behavior: int, optional
        :param win_condition: Win condition for new race format, defaults to None
        :type win_condition: int, optional
        :param number_laps_win: Lap count setting for new race format, defaults to None
        :type number_laps_win: int, optional
        :param team_racing_mode: Team racing setting for new race format, defaults to None
        :type team_racing_mode: bool, optional
        :param points_method: JSON-serialized arguments for new race format, defaults to None
        :type points_method: str, optional
        :return: The created :class:`RaceFormat`
        :rtype: RaceFormat
        """
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
        """All custom attributes assigned to race format.

        :param raceformat_or_id: Either the race format object or the ID of race format
        :type raceformat_or_id: int
        :return: List of :class:`RaceFormatAttribute`
        :rtype: list[RaceFormatAttribute]
        """
        return self._racecontext.rhdata.get_raceformat_attributes(raceformat_or_id)

    @callWithDatabaseWrapper
    def raceformat_attribute_value(self, raceformat_or_id, name, default_value=None):
        """The value of a single custom attribute assigned to race format.

        :param raceformat_or_id: Either the race format object or the ID of race format
        :type raceformat_or_id: RaceFormat|int
        :param name: Attribute to retrieve
        :type name: str
        :param default_value: Value to return if attribute is not registered (uses registered default if available), defaults to None
        :type default_value: any, optional
        :return: Returns string regardless of registered field type, or default value.
        :rtype: str
        """
        for field in self._racecontext.rhui.raceformat_attributes:
            if field.name == name:
                return self._racecontext.rhdata.get_raceformat_attribute_value(raceformat_or_id, field.name, field.value)
        else:
            return self._racecontext.rhdata.get_raceformat_attribute_value(raceformat_or_id, name, default_value)

    @callWithDatabaseWrapper
    def raceformat_ids_by_attribute(self, name, value):
        """ID of race formats with attribute matching the specified attribute/value combination.

        :param name: Attribute to match
        :type name: str
        :param value: Value to match
        :type value: str
        :return: List of race format IDs
        :rtype: list[int]
        """
        return self._racecontext.rhdata.get_raceformat_id_by_attribute(name, value)

    @callWithDatabaseWrapper
    def raceformat_duplicate(self, source_format_or_id):
        """Duplicate a race format.

        :param source_format_or_id: Either a race format object or the ID of a race format
        :type source_format_or_id: RaceFormat|int
        :return: The created :class:`RaceFormat`
        :rtype: RaceFormat
        """
        return self._racecontext.rhdata.duplicate_raceFormat(source_format_or_id)

    @callWithDatabaseWrapper
    def raceformat_alter(self, raceformat_id, name=None, unlimited_time=None, race_time_sec=None, lap_grace_sec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None, points_settings=None, attributes=None):
        """Alter race format data.

        :param raceformat_id: ID of race format to alter
        :type raceformat_id: int
        :param name: Name for new race format, defaults to None
        :type name: str, optional
        :param unlimited_time: Unlimited Time setting for new race format, defaults to None
        :type unlimited_time: int, optional
        :param race_time_sec: Race duration for new race format, defaults to None
        :type race_time_sec: int, optional
        :param lap_grace_sec: Grace period for new race format, defaults to None
        :type lap_grace_sec: int, optional
        :param staging_fixed_tones: Fixed tones for new race format, defaults to None
        :type staging_fixed_tones: int, optional
        :param staging_delay_tones: Delay tones setting for new race format, defaults to None
        :type staging_delay_tones: int, optional
        :param start_delay_min_ms: Delay minimum for new race format, defaults to None
        :type start_delay_min_ms: int, optional
        :param start_delay_max_ms: Maximum delay duration for new race format, defaults to None
        :type start_delay_max_ms: int, optional
        :param start_behavior: First crossing behavior for new race format, defaults to None
        :type start_behavior: int, optional
        :param win_condition: Win condition for new race format, defaults to None
        :type win_condition: int, optional
        :param number_laps_win: Lap count setting for new race format, defaults to None
        :type number_laps_win: int, optional
        :param team_racing_mode: Team racing setting for new race format, defaults to None
        :type team_racing_mode: bool, optional
        :param points_method: JSON-serialized arguments for new race format, defaults to None
        :type points_method: str, optional
        :param points_settings: Arguments to pass to class ranking, defaults to None
        :type points_settings: dict, optional
        :param attributes: Attributes to alter, attribute values assigned to respective keys, defaults to None
        :type attributes: dict, optional
        :return: Returns tuple of this :class:`RaceFormat` and affected races
        :rtype: list[SavedRace]
        """
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
        """Delete race format. Fails if race class has saved races associated, is assigned to the active race, or is the last format in database.

        :param raceformat_id: ID of race format to delete
        :type raceformat_id: int
        :return: Success status
        :rtype: bool
        """
        return self._racecontext.rhdata.delete_raceFormat(raceformat_id)

    @callWithDatabaseWrapper
    def raceformats_reset(self):
        """Resets race formats to default.
        """
        self._racecontext.rhdata.reset_raceFormats()

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
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
        self._racecontext = race_context

    @property
    def results(self):
        return self._racecontext.pagecache.get_cache()


#
# Data input/output
#
class IOAPI():
    def __init__(self, race_context):
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
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
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
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
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
        self._racecontext = race_context

    @property
    def methods(self):
        return self._racecontext.raceclass_rank_manager.methods


#
# Points
#
class PointsAPI():
    def __init__(self, race_context):
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
        self._racecontext = race_context

    @property
    def methods(self):
        return self._racecontext.race_points_manager.methods


#
# LED
#
class LEDAPI():
    def __init__(self, race_context):
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
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
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
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
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
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
    @callWithDatabaseWrapper
    def heat(self, heat_id):
        return self._racecontext.race.set_heat(heat_id)

    @property
    def round(self):
        heat_id = self._racecontext.race.current_heat
        if heat_id:
            round_idx = self._racecontext.rhdata.get_max_round(heat_id)
            if type(round_idx) is int:
                return round_idx + 1
        return 0

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
        return self._racecontext.race.node_laps

    @property
    def laps_active_raw(self, filter_late_laps=False):
        return self._racecontext.race.get_active_laps(filter_late_laps)

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
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
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
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
        self._racecontext = race_context

    @property
    def seats(self):
        return self._racecontext.interface.nodes


#
# Server Config
#
class ServerConfigAPI():
    def __init__(self, race_context):
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
        self._racecontext = race_context

    @property
    def config(self):
        return copy.deepcopy(self._racecontext.serverconfig.config)

    def get_item(self, section, item, as_int=False):
        if as_int:
            return self._racecontext.serverconfig.get_item_int(section, item)
        else:
            return self._racecontext.serverconfig.get_item(section, item)


    def set_item(self, section, item, value):
        return self._racecontext.serverconfig.set_item(section, item, value)


#
# Sensors
#
class SensorsAPI():
    def __init__(self, race_context):
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
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
        """Constructor method

        :param race_context: A handle to the :class:`RaceContext.RaceContext`
        :type race_context: :class:`RaceContext`
        """
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

