"""View and manage the currently active race."""

from Database import LapSource
from RHUtils import callWithDatabaseWrapper

_racecontext = None

@property
def pilots():
    """`Read Only` Pilot IDs, indexed by seat. To change pilots, adjust the corresponding heat 

    :return: List of pilot IDs
    :rtype: list[int]
    """
    return _racecontext.race.node_pilots

@property
def teams():
    """`Read Only` Team of each pilot, indexed by seat. To change teams, adjust the corresponding pilot (identified by matching seat index in :attr:`RaceAPI.pilots`)

    :return: List of teams
    :rtype: list[string]
    """
    return _racecontext.race.node_teams

@property
def slots():
    """`Read Only` Total number of seats/slots.

    :return: Number of slots
    :rtype: int
    """
    return _racecontext.race.num_nodes

@property
def seat_colors():
    """`Read Only` Active color for each seat, indexed by seat.

    :return: List of :class:`Color`
    :rtype: list[Color]
    """
    return _racecontext.race.seat_colors

@property
def heat():
    """`Read Only` ID of assigned heat. None is practice mode. To change active heat options, adjust the assigned heat.

    :return: Heat ID or None
    :rtype: int|None
    """
    return _racecontext.race.current_heat

@heat.setter
@callWithDatabaseWrapper
def heat(heat_id):
    """ID of assigned heat. None is practice mode. To change active heat options, adjust the assigned heat.

    :param heat_id: Heat ID or None
    :type heat_id: int
    """
    return _racecontext.race.set_heat(heat_id)

@property
def round():
    """`Read Only` _summary_

    :return: _description_
    :rtype: _type_
    """
    heat_id = _racecontext.race.current_heat
    if heat_id:
        round_idx = _racecontext.rhdata.get_max_round(heat_id)
        if type(round_idx) is int:
            return round_idx + 1
    return 0

@property
@callWithDatabaseWrapper
def frequencyset():
    """`Read Only` ID of current frequency set. To change active frequency set options, adjust the assigned frequency set.

    :return: Frequency set ID
    :rtype: int
    """
    return _racecontext.race.profile

@frequencyset.setter
@callWithDatabaseWrapper
def frequencyset(set_id):
    """ID of current frequency set. To change active frequency set options, adjust the assigned frequency set.

    :param set_id: Frequency set ID
    :type set_id: int
    """
    _frequencyset_set({'profile': set_id})

@callWithDatabaseWrapper
def _frequencyset_set(data):
    pass # replaced externally. TODO: Refactor management functions

@property
@callWithDatabaseWrapper
def raceformat():
    """`Read Only` Active race format object. Returns None if timer is in secondary mode. To change active format options, adjust the assigned race format.

    :return: RaceFormat or None
    :rtype: RaceFormat|None
    """
    return _racecontext.race.format

@raceformat.setter
@callWithDatabaseWrapper
def raceformat(format_id):
    """Active race format object. Returns None if timer is in secondary mode. To change active format options, adjust the assigned race format.

    :param format_id: RaceFormat or None
    :type format_id: RaceFormat|None
    """
    _raceformat_set({'race_format': format_id})

def _raceformat_set(data):
    pass # replaced externally. TODO: Refactor management functions

@property
def status():
    """`Read Only` Current status of system.

    :return: Status of system
    :rtype: RaceStatus
    """
    return _racecontext.race.race_status

@property
def stage_time_internal():
    """`Read Only` Internal (monotonic) timestamp of race staging start time.

    :return: timestamp
    :rtype: int
    """
    return _racecontext.race.stage_time_monotonic

@property
def start_time():
    """`Read Only` System timestamp of race start time. 

    :return: :class:`datetime.datetime` of race start
    :rtype: datetime.datetime
    """
    return _racecontext.race.start_time

@property
def start_time_internal():
    """`Read Only` Internal (monotonic) timestamp of race start time. Is a future time during staging.

    :return: timestamp
    :rtype: int
    """
    return _racecontext.race.start_time_monotonic

@property
def end_time_internal():
    """`Read Only` Internal (monotonic) timestamp of race end time. Invalid unless :attr:`RaceAPI.status` is :attr:`RHRace.RaceStatus.DONE`

    :return: timestamp
    :rtype: int
    """
    return _racecontext.race.end_time

@property
def seats_finished():
    """`Read Only` Flag indicating whether pilot in a seat has completed all laps.

    :return: Returns dict with the format {id(int) : value(boolean)}
    :rtype: dict
    """
    return _racecontext.race.node_has_finished

@property
@callWithDatabaseWrapper
def laps():
    """`Read Only` Calculated lap results.

    :return: Results
    :rtype: dict
    """
    return _racecontext.race.get_lap_results()

@property
def any_laps_recorded():
    """`Read Only` Whether any laps have been recorded for this race. 

    :return: bool of laps recorded
    :rtype: bool
    """
    return _racecontext.race.any_laps_recorded()

@property
def laps_raw():
    """`Read Only` All lap data.

    :return: All lap data
    :rtype: list[dict]
    """
    return _racecontext.race.node_laps

@property
def laps_active_raw(filter_late_laps=False):
    """`Read Only` All lap data, removing deleted laps.

    :param filter_late_laps:  Set True to also remove laps flagged as late, defaults to False
    :type filter_late_laps: bool, optional
    :return: Lap data
    :rtype: list[dict]
    """
    return _racecontext.race.get_active_laps(filter_late_laps)

def lap_add(seat_index, timestamp):
    """_summary_

    :param seat_index: _description_
    :type seat_index: _type_
    :param timestamp: _description_
    :type timestamp: _type_
    :return: _description_
    :rtype: _type_
    """
    seat = _racecontext.interface.nodes[seat_index]
    return _racecontext.race.add_lap(seat, timestamp, LapSource.API)

@property
@callWithDatabaseWrapper
def results():
    """`Read Only` Calculated race results.

    :return: Race results
    :rtype: dict
    """
    return _racecontext.race.get_results()

@property
@callWithDatabaseWrapper
def team_results():
    """`Read Only` Calculated race team results.

    :return: dict, or None if not in team mode.
    :rtype: dict|None
    """
    return _racecontext.race.get_team_results()

@property
def win_status():
    """`Read Only` Internal (monotonic) timestamp of scheduled race staging start time.

    :return: Returns int, or None if race is not scheduled.
    :rtype: int|None
    """
    return _racecontext.race.win_status

@property
def race_winner_name():
    """`Read Only` _summary_

    :return: _description_
    :rtype: _type_
    """
    return _racecontext.race.race_winner_name

@property
def race_winner_phonetic():
    """`Read Only` _summary_

    :return: _description_
    :rtype: _type_
    """
    return _racecontext.race.race_winner_phonetic

@property
def race_winner_lap_id():
    """`Read Only` _summary_

    :return: _description_
    :rtype: _type_
    """
    return _racecontext.race.race_winner_lap_id

@property
def race_winner_pilot_id():
    """`Read Only` _summary_

    :return: _description_
    :rtype: _type_
    """
    return _racecontext.race.race_winner_pilot_id

@property
def race_leader_lap():
    """`Read Only` _summary_

    :return: _description_
    :rtype: _type_
    """
    return _racecontext.race.race_leader_lap

@property
def race_leader_pilot_id():
    """`Read Only` _summary_

    :return: _description_
    :rtype: _type_
    """
    return _racecontext.race.race_leader_pilot_id

def schedule(sec_or_none, minutes=0):
    """Schedule race with a relative future time offset. Fails if :attr:`RaceAPI.status` is not :attr:`RHRace.RaceStatus.READY`. Cancels existing schedule if both values are false.

    :param sec_or_none: Seconds ahead to schedule race
    :type sec_or_none: int|None
    :param minutes: Minutes ahead to schedule race, defaults to 0
    :type minutes: int, optional
    :return: Success value
    :rtype: bool
    """
    return _racecontext.race.schedule(sec_or_none, minutes)

@property
def scheduled():
    """`Read Only` Internal (monotonic) timestamp of scheduled race staging start time.

    :return: Returns int, or None if race is not scheduled.
    :rtype: int|None
    """
    if _racecontext.race.scheduled:
        return _racecontext.race.scheduled_time
    else:
        return None

def stage(args=None):
    """Begin race staging sequence. May fail if :attr:`RaceAPI.status` is not :attr:`RHRace.RaceStatus.READY`.

    :param args: _description_, defaults to None
    :type args: _type_, optional
    """
    _racecontext.race.stage(args)

def stop(doSave=False):
    """Stop race.

    :param doSave: Run race data save routines immediately after stopping, defaults to False
    :type doSave: bool, optional
    """
    _racecontext.race.stop(doSave)

def save():
    """Save laps and clear race data. May activate heat advance and other procedures."""
    _racecontext.race.save()

def clear():
    """Clear laps and reset :attr:`RaceAPI.status` to :attr:`RHRace.RaceStatus.READY`. Fails if :attr:`RaceAPI.status` is :attr:`RHRace.RaceStatus.STAGING` or :attr:`RHRace.RaceStatus.RACING` — stop race before using."""
    _racecontext.race.discard_laps()