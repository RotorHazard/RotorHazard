"""Read and modify database values."""

import json
import logging
from RHUI import UIFieldType
from RHUtils import callWithDatabaseWrapper

_racecontext = None

logger = logging.getLogger(__name__)

@callWithDatabaseWrapper
def reset_all():
    """Resets database to default state.

    :return: Database successfully reset 
    :rtype: bool
    """
    return _racecontext.rhdata.reset_all()

# Pilot

@property
@callWithDatabaseWrapper
def pilots():
    """`Read Only` All pilot records

    :return: Pilot records
    :rtype: list[Pilot]
    """
    return _racecontext.rhdata.get_pilots()

@callWithDatabaseWrapper
def pilot_by_id(pilot_id):
    """A single pilot record. Does not include custom attributes.

    :param pilot_id: ID of pilot record to retrieve
    :type pilot_id: int
    :return: created pilot record
    :rtype: Pilot
    """
    return _racecontext.rhdata.get_pilot(pilot_id)

@callWithDatabaseWrapper
def pilot_attributes(pilot_or_id):
    """All custom attributes assigned to pilot.

    :param pilot_or_id: Either the pilot object or the ID of pilot
    :type pilot_or_id: Pilot|int
    :return: A pilot's attributes
    :rtype: list[PilotAttribute]
    """
    return _racecontext.rhdata.get_pilot_attributes(pilot_or_id)

@callWithDatabaseWrapper
def pilot_attribute_value(pilot_or_id, name, default_value=None):
    """The value of a single custom attribute assigned to pilot

    :param pilot_or_id: Either the pilot object or the ID of pilot
    :type pilot_or_id: Pilot|int
    :param name: Attribute to match
    :type name: str
    :param default_value: value to return if attribute is not registered (uses registered default if available), defaults to None
    :type default_value: any, optional
    :return: A :class:`Database.PilotAttribute`
    :rtype: PilotAttribute
    """
    for field in _racecontext.rhui.pilot_attributes:
        if field.name == name:
            return _racecontext.rhdata.get_pilot_attribute_value(pilot_or_id, field.name, field.value)
    else:
        return _racecontext.rhdata.get_pilot_attribute_value(pilot_or_id, name, default_value)

@callWithDatabaseWrapper
def pilot_ids_by_attribute(name, value):
    """ID of pilots with attribute matching the specified attribute/value combination

    :param name: Attribute to match
    :type name: str
    :param value: Value to match
    :type value: str
    :return: Pilots' IDs
    :rtype: list[int]
    """
    return _racecontext.rhdata.get_pilot_id_by_attribute(name, value)

@callWithDatabaseWrapper
def pilot_add(name=None, callsign=None, phonetic=None, team=None, color=None):
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
    :return: Created :class:`Database.Pilot`
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

    return _racecontext.rhdata.add_pilot(data)

@callWithDatabaseWrapper
def pilot_alter(pilot_id, name=None, callsign=None, phonetic=None, team=None, color=None, attributes=None):
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
    :return: Altered :class:`Database.Pilot`
    :rtype: Pilot
    """
    data = {}

    if isinstance(attributes, dict):
        data['pilot_id'] = pilot_id
        for key, value in attributes.items():
            data['pilot_attr'] = key
            data['value'] = value
            _racecontext.rhdata.alter_pilot(data)

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
        return _racecontext.rhdata.alter_pilot(data)

@callWithDatabaseWrapper
def pilot_delete(pilot_or_id):
    """Delete pilot record. Fails if pilot is associated with saved race.

    :param pilot_or_id: ID of pilot to delete
    :type pilot_or_id: int
    :return: Delete success status.
    :rtype: bool
    """
    return _racecontext.rhdata.delete_pilot(pilot_or_id)

@callWithDatabaseWrapper
def pilots_reset():
    """Delete all pilot records.

    :return: Reset status
    :rtype: bool
    """
    return _racecontext.rhdata.reset_pilots()

# Heat

@property
@callWithDatabaseWrapper
def heats():
    """`Read Only` All heat records.

    :return: List of :class:`Database.Heat`
    :rtype: list[Heat]
    """
    return _racecontext.rhdata.get_heats()

@callWithDatabaseWrapper
def heat_by_id(heat_id):
    """A single heat record.

    :param heat_id: ID of heat record to retrieve
    :type heat_id: int
    :return: heat record
    :rtype: Heat
    """
    return _racecontext.rhdata.get_heat(heat_id)

@callWithDatabaseWrapper
def heat_attributes(heat_or_id):
    """All custom attributes assigned to heat.

    :param heat_or_id: Either the heat object or the ID of heat
    :type heat_or_id: Heat|int
    :return: Heat's attributes
    :rtype: list[HeatAttribute]
    """
    return _racecontext.rhdata.get_heat_attributes(heat_or_id)

@callWithDatabaseWrapper
def heat_attribute_value(heat_or_id, name, default_value=None):
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
    for field in _racecontext.rhui.heat_attributes:
        if field.name == name:
            return _racecontext.rhdata.get_heat_attribute_value(heat_or_id, field.name, field.value)
    else:
        return _racecontext.rhdata.get_heat_attribute_value(heat_or_id, name, default_value)

@callWithDatabaseWrapper
def heat_ids_by_attribute(name, value):
    """ID of heats with attribute matching the specified attribute/value combination.

    :param name: Name for new heat
    :type name: str, optional
    :param value: Raceclass ID for new heat
    :type value: int, optional
    :return: List of heat IDs
    :rtype: list[int]
    """
    return _racecontext.rhdata.get_heat_id_by_attribute(name, value)

@callWithDatabaseWrapper
def heats_by_class(raceclass_id):
    """All heat records associated with a specific class.

    :param raceclass_id: ID of raceclass used to retrieve heats
    :type raceclass_id: int
    :return: List of heats
    :rtype: list[Heat]
    """
    return _racecontext.rhdata.get_heats_by_class(raceclass_id)

@callWithDatabaseWrapper
def heat_results(heat_or_id):
    """The calculated summary result set for all races associated with this heat.

    :param heat_or_id: Either the heat object or the ID of heat
    :type heat_or_id: Heat|int
    :return: heat results
    :rtype: dict
    """
    return _racecontext.rhdata.get_results_heat(heat_or_id)

@callWithDatabaseWrapper
def heat_max_round(heat_id):
    """The highest-numbered race round recorded for selected heat.

    :param heat_id: ID of heat
    :type heat_id: int
    :return: Round number
    :rtype: int
    """
    return _racecontext.rhdata.get_max_round(heat_id)

@callWithDatabaseWrapper
def heat_add(name=None, raceclass=None, auto_frequency=None):
    """Add a new heat to the database.

    :param name: Name for new heat, defaults to None
    :type name: string, optional
    :param raceclass: Raceclass ID for new heat, defaults to None
    :type raceclass: int, optional
    :param auto_frequency: Whether to enable auto-frequency, defaults to None
    :type auto_frequency: bool, optional
    :return: The new :class:`Database.Heat`
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

    return _racecontext.rhdata.add_heat(data)

@callWithDatabaseWrapper
def heat_duplicate(source_heat_or_id, dest_class=None):
    """Duplicate a heat record.

    :param source_heat_or_id: Either the heat object or the ID of heat to copy from
    :type source_heat_or_id: Heat|int
    :param dest_class: Raceclass ID to copy heat into, defaults to None
    :type dest_class: int, optional
    :return: The new :class:`Database.Heat`
    :rtype: Heat
    """
    if dest_class:
        return _racecontext.rhdata.duplicate_heat(source_heat_or_id, dest_class=dest_class)
    else:
        return _racecontext.rhdata.duplicate_heat(source_heat_or_id)

@callWithDatabaseWrapper
def heat_alter(heat_id, name=None, raceclass=None, auto_frequency=None, status=None, attributes=None):
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
    :rtype: list[SavedRaceMeta]
    """
    data = {}

    if isinstance(attributes, dict):
        data['heat'] = heat_id
        for key, value in attributes.items():
            data['heat_attr'] = key
            data['value'] = value
            _racecontext.rhdata.alter_heat(data)

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
        return _racecontext.rhdata.alter_heat(data)

@callWithDatabaseWrapper
def heat_delete(heat_or_id):
    """Delete heat. Fails if heat has saved races associated or if there is only one heat left in the database.

    :param heat_or_id: ID of heat to delete
    :type heat_or_id: Heat|int
    :return: Success status
    :rtype: bool
    """
    return _racecontext.rhdata.delete_heat(heat_or_id)

@callWithDatabaseWrapper
def heats_reset():
    """Delete all heat records
    """
    _racecontext.rhdata.reset_heats()

# Heat -> Slots

@property
@callWithDatabaseWrapper
def slots():
    """`Read Only` All slot records.

    :return: List of HeatNode
    :rtype: list[HeatNode]
    """
    return _racecontext.rhdata.get_heatNodes()

@callWithDatabaseWrapper
def slots_by_heat(heat_id):
    """Slot records associated with a specific heat.

    :param heat_id: ID of heat used to retrieve slots
    :type heat_id: int
    :return: List of HeatNode
    :rtype: list[HeatNode]
    """
    return _racecontext.rhdata.get_heatNodes_by_heat(heat_id)

@callWithDatabaseWrapper
def slot_alter(slot_id, method=None, pilot=None, seed_heat_id=None, seed_raceclass_id=None, seed_rank=None):
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
    :rtype: list[SavedRaceMeta]

    With method set to :attr:`Database.ProgramMethod.NONE`, most other fields are ignored. Only use seed_heat_id with :attr:`Database.ProgramMethod.HEAT_RESULT`, and seed_raceclass_id with :attr:`Database.ProgramMethod.CLASS_RESULT`, otherwise the assignment is ignored.
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
        slot = _racecontext.rhdata.get_heatNode(slot_id)
        heat_id = slot.heat_id

        data['heat'] = heat_id
        data['slot_id'] = slot_id
        return _racecontext.rhdata.alter_heat(data)

@callWithDatabaseWrapper
def slots_alter_fast(slot_list):
    """Make many alterations to slots in a single database transaction as quickly as possible. Use with caution. May accept invalid input. Does not trigger events, clear associated results, or update cached data. These operations must be done manually if required.

    Input dict parameters match the parameters used in :meth:`DatabaseAPI.slot_alter` 

    :param slot_list: List of dicts containing parameters for each slot
    :type slot_list: list[dict]
    """
    # !! Unsafe for general use !!
    _racecontext.rhdata.alter_heatNodes_fast(slot_list)

# Race Class

@property
@callWithDatabaseWrapper
def raceclasses():
    """`Read Only` All race class records.

    :return: System race classes
    :rtype: list[RaceClass]
    """
    return _racecontext.rhdata.get_raceClasses()

@callWithDatabaseWrapper
def raceclass_by_id(raceclass_id):
    """A single race class record.

    :param raceclass_id: ID of race class record to retrieve
    :type raceclass_id: int
    :return: The race class
    :rtype: RaceClass
    """
    return _racecontext.rhdata.get_raceClass(raceclass_id)

@callWithDatabaseWrapper
def raceclass_attributes(raceclass_or_id):
    """All custom attributes assigned to race class.

    :param raceclass_or_id: Either the race class object or the ID of race class
    :type raceclass_or_id: Raceclass|int
    :return: The class's race class attributes
    :rtype: list[RaceClassAttribute]
    """
    return _racecontext.rhdata.get_raceclass_attributes(raceclass_or_id)

@callWithDatabaseWrapper
def raceclass_attribute_value(raceclass_or_id, name, default_value=None):
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
    for field in _racecontext.rhui.raceclass_attributes:
        if field.name == name:
            return _racecontext.rhdata.get_raceclass_attribute_value(raceclass_or_id, field.name, field.value)
    else:
        return _racecontext.rhdata.get_raceclass_attribute_value(raceclass_or_id, name, default_value)

@callWithDatabaseWrapper
def raceclass_ids_by_attribute(name, value):
    """ID of race classes with attribute matching the specified attribute/value combination.

    :param name: Attribute to match
    :type name: str
    :param value: Value to match
    :type value: str
    :return: List of pilots
    :rtype: list[int]
    """
    return _racecontext.rhdata.get_raceclass_id_by_attribute(name, value)

@callWithDatabaseWrapper
def raceclass_add(name=None, description=None, raceformat=None, win_condition=None, rounds=None, heat_advance_type=None):
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
    :return: The created :class:`Database.RaceClass`
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
        return _racecontext.rhdata.add_raceClass(data)

@callWithDatabaseWrapper
def raceclass_duplicate(source_class_or_id):
    """Duplicate a race class.

    :param source_class_or_id: Either a race class object or the ID of a race class
    :type source_class_or_id: RaceClass|int
    :return: The created :class:`Database.RaceClass`
    :rtype: RaceClass
    """
    return _racecontext.rhdata.duplicate_raceClass(source_class_or_id)

@callWithDatabaseWrapper
def raceclass_alter(raceclass_id, name=None, description=None, raceformat=None, win_condition=None, rounds=None, heat_advance_type=None, rank_settings=None, attributes=None):
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
    :return: Returns tuple of this :class:`Database.RaceClass` and affected races
    :rtype: list[SavedRaceMeta]
    """
    data = {}

    if isinstance(attributes, dict):
        data['class_id'] = raceclass_id
        for key, value in attributes.items():
            data['class_attr'] = key
            data['value'] = value
            _racecontext.rhdata.alter_raceClass(data)

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
        return _racecontext.rhdata.alter_raceClass(data)

@callWithDatabaseWrapper
def raceclass_results(raceclass_or_id):
    """The calculated summary result set for all races associated with this race class.

    :param raceclass_or_id: Either the race class object or the ID of race class
    :type raceclass_or_id: RaceClass|int
    :return: Results for race class
    :rtype: dict
    """
    return _racecontext.rhdata.get_results_raceClass(raceclass_or_id)

@callWithDatabaseWrapper
def raceclass_ranking(raceclass_or_id):
    """The calculated ranking associated with this race class.

    :param raceclass_or_id: Either the race class object or the ID of race class
    :type raceclass_or_id: RaceClass
    :return: Rankings for race class
    :rtype: dict
    """
    return _racecontext.rhdata.get_ranking_raceClass(raceclass_or_id)

@callWithDatabaseWrapper
def raceclass_delete(raceclass_or_id):
    """Delete race class. Fails if race class has saved races associated.

    :param raceclass_or_id: Either the race class object or the ID of race class
    :type raceclass_or_id: RaceClass|int
    :return: Success status
    :rtype: bool
    """
    return _racecontext.rhdata.delete_raceClass(raceclass_or_id)

@callWithDatabaseWrapper
def raceclasses_reset():
    """Delete all race classes.
    """
    _racecontext.rhdata.reset_raceClasses()

# Race Format

@property
@callWithDatabaseWrapper
def raceformats():
    """`Read Only` All race formats.

    :return: System race formats
    :rtype: list[RaceFormat]
    """
    return _racecontext.rhdata.get_raceFormats()

@callWithDatabaseWrapper
def raceformat_by_id(format_id):
    """A single race format record.

    :param format_id: ID of race format record to retrieve
    :type format_id: int
    :return: The race format
    :rtype: RaceFormat
    """
    return _racecontext.rhdata.get_raceFormat(format_id)

@callWithDatabaseWrapper
def raceformat_add(name=None, unlimited_time=None, race_time_sec=None, lap_grace_sec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None):
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
    :return: The created :class:`Database.RaceFormat`
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

    return _racecontext.rhdata.add_format(data)

@callWithDatabaseWrapper
def raceformat_attributes(raceformat_or_id):
    """All custom attributes assigned to race format.

    :param raceformat_or_id: Either the race format object or the ID of race format
    :type raceformat_or_id: int
    :return: List of :class:`Database.RaceFormatAttribute`
    :rtype: list[RaceFormatAttribute]
    """
    return _racecontext.rhdata.get_raceformat_attributes(raceformat_or_id)

@callWithDatabaseWrapper
def raceformat_attribute_value(raceformat_or_id, name, default_value=None):
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
    for field in _racecontext.rhui.raceformat_attributes:
        if field.name == name:
            return _racecontext.rhdata.get_raceformat_attribute_value(raceformat_or_id, field.name, field.value)
    else:
        return _racecontext.rhdata.get_raceformat_attribute_value(raceformat_or_id, name, default_value)

@callWithDatabaseWrapper
def raceformat_ids_by_attribute(name, value):
    """ID of race formats with attribute matching the specified attribute/value combination.

    :param name: Attribute to match
    :type name: str
    :param value: Value to match
    :type value: str
    :return: List of race format IDs
    :rtype: list[int]
    """
    return _racecontext.rhdata.get_raceformat_id_by_attribute(name, value)

@callWithDatabaseWrapper
def raceformat_duplicate(source_format_or_id):
    """Duplicate a race format.

    :param source_format_or_id: Either a race format object or the ID of a race format
    :type source_format_or_id: RaceFormat|int
    :return: The created :class:`Database.RaceFormat`
    :rtype: RaceFormat
    """
    return _racecontext.rhdata.duplicate_raceFormat(source_format_or_id)

@callWithDatabaseWrapper
def raceformat_alter(raceformat_id, name=None, unlimited_time=None, race_time_sec=None, lap_grace_sec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None, points_settings=None, attributes=None):
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
    :return: Returns tuple of this :class:`Database.RaceFormat` and affected races
    :rtype: list[SavedRaceMeta]
    """
    data = {}

    if isinstance(attributes, dict):
        data['format_id'] = raceformat_id
        for key, value in attributes.items():
            data['format_attr'] = key
            data['value'] = value
            _racecontext.rhdata.alter_raceFormat(data)

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
        return _racecontext.rhdata.alter_raceFormat(data)

@callWithDatabaseWrapper
def raceformat_delete(raceformat_id):
    """Delete race format. Fails if race class has saved races associated, is assigned to the active race, or is the last format in database.

    :param raceformat_id: ID of race format to delete
    :type raceformat_id: int
    :return: Success status
    :rtype: bool
    """
    return _racecontext.rhdata.delete_raceFormat(raceformat_id)

@callWithDatabaseWrapper
def raceformats_reset():
    """Resets race formats to default.
    """
    _racecontext.rhdata.reset_raceFormats()

# Frequency Sets (Profiles)

@property
@callWithDatabaseWrapper
def frequencysets():
    """`Read Only` All frequency set records.

    :return: List of :class:`Database.Profiles`
    :rtype: list[Profiles]
    """
    return _racecontext.rhdata.get_profiles()

@callWithDatabaseWrapper
def frequencyset_by_id(set_id):
    """A single frequency set record.

    :param set_id: ID of frequency set record to retrieve
    :type set_id: int
    :return: The frequency :class:`Database.Profiles`
    :rtype: Profiles
    """
    return _racecontext.rhdata.get_profile(set_id)

@callWithDatabaseWrapper
def frequencyset_add(name=None, description=None, frequencies=None, enter_ats=None, exit_ats=None):
    """Add a new frequency set to the database.

    :param name: Name for new frequency set, defaults to None
    :type name: str, optional
    :param description: Description for new frequency set, defaults to None
    :type description: str, optional
    :param frequencies: Frequency, band, and channel information for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form, defaults to None
    :type frequencies: str|dict, optional
    :param enter_ats: Enter-at points for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form, defaults to None
    :type enter_ats: string|dict, optional
    :param exit_ats: Exit-at points for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form, defaults to None
    :type exit_ats: string|dict, optional
    :return: The created :class:`Database.Profiles`
    :rtype: Profiles
    """
    data = {}

    source_profile = _racecontext.race.profile
    new_profile = _racecontext.rhdata.duplicate_profile(source_profile) 

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
        new_profile = _racecontext.rhdata.alter_profile(data)

    return new_profile

@callWithDatabaseWrapper
def frequencyset_duplicate(source_set_or_id):
    """Duplicate a frequency set.

    :param source_set_or_id: Either a frequency set object or the ID of a frequency set
    :type source_set_or_id: Profiles|int
    :return: The created :class:`Database.Profiles`
    :rtype: Profiles
    """
    return _racecontext.rhdata.duplicate_profile(source_set_or_id)

@callWithDatabaseWrapper
def frequencyset_alter(set_id, name=None, description=None, frequencies=None, enter_ats=None, exit_ats=None):
    """Alter frequency set data.

    :param set_id: ID of frequency set to alter
    :type set_id: int
    :param name: Name for new frequency set, defaults to None
    :type name: str, optional
    :param description: Description for new frequency set, defaults to None
    :type description: str, optional
    :param frequencies: Frequency, band, and channel information for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form, defaults to None
    :type frequencies: str|dict, optional
    :param enter_ats: Enter-at points for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form, defaults to None
    :type enter_ats: str|dict, optional
    :param exit_ats: Exit-at points for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form, defaults to None
    :type exit_ats: str|dict, optional
    :return: The altered :class:`Database.Profiles` object
    :rtype: Profiles
    """
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
        result = _racecontext.rhdata.alter_profile(data)

        if set_id == _racecontext.race.profile.id:
            _racecontext.race.profile = result
            for idx, value in enumerate(json.loads(result.frequencies)['f']):
                if idx < _racecontext.race.num_nodes:
                    _racecontext.interface.set_frequency(idx, value)
            _racecontext.rhui.emit_frequency_data()

        return result

@callWithDatabaseWrapper
def frequencyset_delete(set_or_id):
    """Delete frequency set. Fails if frequency set is last remaining.

    :param set_or_id: Either a frequency set object or the ID of a frequency set
    :type set_or_id: Profiles|int
    :return: Success status
    :rtype: bool
    """
    return _racecontext.rhdata.delete_profile(set_or_id)

@callWithDatabaseWrapper
def frequencysets_reset():
    """Resets frequency sets to default."""
    _racecontext.rhdata.reset_profiles()

# Saved Race

@property
@callWithDatabaseWrapper
def races():
    """`Read Only` All saved race records.

    :return: The system's saved race records
    :rtype: list[SavedRaceMeta]
    """
    return _racecontext.rhdata.get_savedRaceMetas()

@callWithDatabaseWrapper
def race_by_id(race_id):
    """A single saved race record, retrieved by ID.

    :param race_id: ID of saved race record to retrieve
    :type race_id: int
    :return: The race record
    :rtype: SavedRaceMeta
    """
    return _racecontext.rhdata.get_savedRaceMeta(race_id)

@callWithDatabaseWrapper
def race_attributes(race_or_id):
    """All custom attributes assigned to race.

    :param race_or_id: Either the race object or the ID of race
    :type race_or_id: SavedRaceMeta|int
    :return: The race attributes
    :rtype: list[SavedRaceMetaAttribute]
    """
    return _racecontext.rhdata.get_savedrace_attributes(race_or_id)

@callWithDatabaseWrapper
def race_attribute_value(race_or_id, name, default_value=None):
    """The value of a single custom attribute assigned to race.

    :param race_or_id: Either the race object or the ID of race
    :type race_or_id: SavedRaceMeta|int
    :param name: Attribute to retrieve
    :type name: str
    :param default_value: Value to return if attribute is not registered (uses registered default if available), defaults to None
    :type default_value: any, optional
    :return: Returns string regardless of registered field type, or default value.
    :rtype: str
    """
    for field in _racecontext.rhui.savedrace_attributes:
        if field.name == name:
            return _racecontext.rhdata.get_savedrace_attribute_value(race_or_id, field.name, field.value)
    else:
        return _racecontext.rhdata.get_savedrace_attribute_value(race_or_id, name, default_value)

@callWithDatabaseWrapper
def race_ids_by_attribute(name, value):
    """ID of races with attribute matching the specified attribute/value combination.

    :param name: Attribute to match
    :type name: str
    :param value:  Value to match
    :type value: str
    :return: List of race IDs
    :rtype: list[int]
    """
    return _racecontext.rhdata.get_savedrace_id_by_attribute(name, value)

@callWithDatabaseWrapper
def race_by_heat_round(heat_id, round_number):
    """A single saved race record, retrieved by heat and round.

    :param heat_id: ID of heat used to retrieve saved race
    :type heat_id: int
    :param round_number: Round number used to retrieve saved race
    :type round_number: int
    :return: The selected :class:`Database.SavedRaceMeta`
    :rtype: SavedRaceMeta
    """
    return _racecontext.rhdata.get_savedRaceMeta_by_heat_round(heat_id, round_number)

@callWithDatabaseWrapper
def races_by_heat(heat_id):
    """Saved race records matching the provided heat ID.

    :param heat_id: ID of heat used to retrieve saved race
    :type heat_id: heat_id
    :return: List of race records
    :rtype: list[SavedRaceMeta]
    """
    return _racecontext.rhdata.get_savedRaceMetas_by_heat(heat_id)

@callWithDatabaseWrapper
def races_by_raceclass(raceclass_id):
    """Saved race records matching the provided race class ID.

    :param raceclass_id: Saved race records matching the provided race class ID.
    :type raceclass_id: int
    :return: List of race records
    :rtype: list[SavedRaceMeta]
    """
    return _racecontext.rhdata.get_savedRaceMetas_by_raceClass(raceclass_id)

@callWithDatabaseWrapper
def race_alter(race_id, attributes=None):
    """Alter race data. Supports only custom attributes.

    :param race_id: ID of race to alter
    :type race_id: int
    :param attributes: Attributes to alter, attribute values assigned to respective keys, defaults to None
    :type attributes: list[dict], optional
    """
    data = {}

    if isinstance(attributes, dict):
        data['race_id'] = race_id
        for key, value in attributes.items():
            data['race_attr'] = key
            data['value'] = value
            _racecontext.rhdata.alter_savedRaceMeta(race_id, data)

@callWithDatabaseWrapper
def race_results(race_or_id):
    """Calculated result set for saved race.

    :param race_or_id: Either the saved race object or the ID of saved race
    :type race_or_id: SavedRaceMeta|int
    :return: Results of race
    :rtype: dict
    """
    return _racecontext.rhdata.get_results_savedRaceMeta(race_or_id)

@callWithDatabaseWrapper
def races_clear():
    """Delete all saved races."""
    _racecontext.rhdata.clear_race_data()

# Race -> Pilot Run

@property
@callWithDatabaseWrapper
def pilotruns():
    """`Read Only` All pilot run records.

    :return: List of :class:`Database.SavedPilotRace`
    :rtype: list[SavedPilotRace]
    """
    return _racecontext.rhdata.get_savedPilotRaces()

@callWithDatabaseWrapper
def pilotrun_by_id(run_id):
    """A single pilot run record, retrieved by ID.

    :param run_id: ID of pilot run record to retrieve
    :type run_id: int
    :return: The :class:`Database.SavedPilotRace`
    :rtype: SavedPilotRace
    """
    return _racecontext.rhdata.get_savedPilotRace(run_id)

@callWithDatabaseWrapper
def pilotruns_by_race(race_id):
    """Pilot run records matching the provided saved race ID.

    :param race_id: ID of saved race used to retrieve pilot runs
    :type race_id: int
    :return: A list of :class:`Database.SavedPilotRace`
    :rtype: list[SavedPilotRace]
    """
    return _racecontext.rhdata.get_savedPilotRaces_by_savedRaceMeta(race_id)

# Race -> Pilot Run -> Laps

@property
@callWithDatabaseWrapper
def laps():
    """`Read Only` All lap records.

    :return: A list of :class:`Database.SavedRaceLap`
    :rtype: list[SavedRaceLap]
    """
    return _racecontext.rhdata.get_savedRaceLaps()

@callWithDatabaseWrapper
def laps_by_pilotrun(run_id):
    """Lap records matching the provided pilot run ID.

    :param run_id: ID of pilot run used to retrieve laps
    :type run_id: int
    :return: A list of :class:`Database.SavedRaceLap`
    :rtype: list[SavedRaceLap]
    """
    return _racecontext.rhdata.get_savedRaceLaps_by_savedPilotRace(run_id)

@callWithDatabaseWrapper
def lap_splits():
    """_summary_

    :return: _description_
    :rtype: _type_
    """
    return _racecontext.rhdata.get_lapSplits()

# Options

@property
@callWithDatabaseWrapper
def options():
    """`Read Only` All options.

    :return: A list of :class:`Database.GlobalSettings`
    :rtype: list[GlobalSettings]
    """
    return _racecontext.rhdata.get_options()

@callWithDatabaseWrapper
def option(name, default=False, as_int=False):
    """Value of option with the provided name.

    :param name: Name of option to retrieve
    :type name: str
    :param default: Value to return if option does not exist, defaults to False
    :type default: str, optional
    :param as_int: Return value as integer instead of string, defaults to False
    :type as_int: bool, optional
    :return: The option value
    :rtype: str
    """
    # Deprecation of options migrated to config
    for item in _racecontext.serverconfig.migrations:
        if item.source == name:
            logger.warning(
                "Deprecation: rhapi.option called for migrated property; use config.get_item('{}', '{}')".format(
                    item.section, name),
                stack_info=True)

            if as_int:
                if default is not False:
                    return _racecontext.serverconfig.get_item_int(item.section, name, default)
                else:
                    return _racecontext.serverconfig.get_item_int(item.section, name)

            if default is not False:
                return _racecontext.serverconfig.get_item(item.section, name, default)
            else:
                return _racecontext.serverconfig.get_item(item.section, name)


    for setting in _racecontext.rhui.general_settings:
        if setting.name == name:
            field = setting.field
            default = field.value
            if field.field_type == UIFieldType.BASIC_INT:
                as_int = True
            break

    if as_int:
        if default is not False:
            return _racecontext.rhdata.get_optionInt(name, default)
        else:
            return _racecontext.rhdata.get_optionInt(name)

    if default is not False:
        return _racecontext.rhdata.get_option(name, default)
    else:
        return _racecontext.rhdata.get_option(name)

@callWithDatabaseWrapper
def option_set(name, value):
    """Set value for the option with provided name.

    :param name: Name of option to alter
    :type name: str
    :param value: New value for option
    :type value: str
    """
    # Deprecation of options migrated to config
    for item in _racecontext.serverconfig.migrations:
        if item.source == name:
            logger.warning(
                "Deprecation: rhapi.option_set called for migrated property; use config.set_item('{}', '{}')".format(
                    item.section, name),
                stack_info=True)
            return _racecontext.serverconfig.set_item(item.section, name, value)

    return _racecontext.rhdata.set_option(name, value)

@callWithDatabaseWrapper
def options_reset():
    """Delete all options."""
    _racecontext.rhdata.reset_options()

# Event

@callWithDatabaseWrapper
def event_results():
    """Returns cumulative totals for all saved races

    :return: Event results
    :rtype: dict
    """
    return _racecontext.rhdata.get_results_event()