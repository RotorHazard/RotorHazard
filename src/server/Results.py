#
# Results generators and caching
#
from typing import List
from RHUI import UIField
from eventmanager import Evt
from filtermanager import Flt
import copy
import json
import gevent
import RHUtils
from RHUtils import catchLogExceptionsWrapper, cleanVarName
import logging
from time import monotonic
from Database import RoundType
from RHRace import RaceStatus, StartBehavior, WinCondition, WinStatus, RacingMode

logger = logging.getLogger(__name__)

from FlaskAppObj import APP
APP.app_context().push()

NONE_NONE_PAIR = [None, None]

in_calc_leaderboard_fn_flag = False

class RaceClassRankManager():
    def __init__(self, RHAPI, Events):
        self._methods = {}
        self._rhapi = RHAPI

        Events.trigger(Evt.CLASS_RANK_INITIALIZE, {
            'register_fn': self.registerMethod
            })

    def registerMethod(self, method):
        if isinstance(method, RaceClassRankMethod):
            if method.name in self.methods:
                logger.warning('Overwriting method "{0}"'.format(method.name))

            self.methods[method.name] = method
        else:
            logger.warning('Invalid method')

    @property
    def methods(self):
        return self._methods

    @catchLogExceptionsWrapper
    def rank(self, method_id, race_class, args=None):
        if method_id == "":
            return False, False

        lb, meta = self.methods[method_id].rank(self._rhapi, race_class, args)
        if 'method_label' not in meta:
            meta['method_label'] = self.methods[method_id].label

        return lb, meta

class RaceClassRankMethod():
    def __init__(self, label, rank_fn, default_args=None, settings:List[UIField]=None, name=None):
        if name is None:
            self.name = cleanVarName(label)
        else:
            self.name = name

        self.label = label
        self.rank_fn = rank_fn
        self.default_args = default_args
        self.settings = settings

    def rank(self, rhapi, race_class, localArgs):
        return self.rank_fn(rhapi, race_class, {**(self.default_args if self.default_args else {}), **(localArgs if localArgs else {})})

class RacePointsManager():
    def __init__(self, RHAPI, Events):
        self._methods = {}
        self._rhapi = RHAPI

        Events.trigger(Evt.POINTS_INITIALIZE, {
            'register_fn': self.registerMethod
            })

    def registerMethod(self, method):
        if hasattr(method, 'name'):
            if method.name in self.methods:
                logger.warning('Overwriting method "{0}"'.format(method.name))

            self.methods[method.name] = method
        else:
            logger.warning('Invalid method')

    @property
    def methods(self):
        return self._methods

    @catchLogExceptionsWrapper
    def assign(self, method_id, leaderboard, args=None):
        if method_id == "":
            return leaderboard

        return self.methods[method_id].assign(self._rhapi, leaderboard, args)

class RacePointsMethod():
    def __init__(self, label, assign_fn, default_args=None, settings:List[UIField]=None, name=None):
        if name is None:
            self.name = cleanVarName(label)
        else:
            self.name = name

        self.label = label
        self.assignFn = assign_fn
        self.default_args = default_args
        self.settings = settings

    def assign(self, rhapi, leaderboard, localArgs):
        return self.assignFn(rhapi, leaderboard, {**(self.default_args if self.default_args else {}), **(localArgs if localArgs else {})})

class LapInfo():
    class race:
        total_pilots: None
        lap_max: None
        consecutives_base: None
        win_condition = None
        best_lap: None
        best_lap_callsign: None
        split_count: None

    class current:
        pilot_id = None
        seat = None
        position = None
        callsign = None
        lap_number = None
        last_lap_time = None
        total_time = None
        total_time_laps = None
        consecutives = None
        is_best_lap = None
        lap_list = None

    class next_rank:
        pilot_id = None
        seat = None
        position = None
        callsign = None
        diff_time = None
        lap_number = None
        last_lap_time = None
        total_time = None

    class first_rank:
        pilot_id = None
        seat = None
        position = None
        callsign = None
        lap_number = None
        last_lap_time = None
        total_time = None

    def __init__(self):
        self.race = self.race()
        self.current = self.current()
        self.next_rank = self.next_rank()
        self.first_rank = self.first_rank()

    def toJSON(self):
        return {
            'race': json.dumps(self.race, default=lambda o: o.__dict__),
            'current': json.dumps(self.current, default=lambda o: o.__dict__),
            'next_rank': json.dumps(self.next_rank, default=lambda o: o.__dict__),
            'first_rank': json.dumps(self.first_rank, default=lambda o: o.__dict__)
        }

    def __repr__(self):
        return json.dumps(self.toJSON())

@catchLogExceptionsWrapper
def build_atomic_results(rhDataObj, params):
    dbg_trace_str = ""
    if logger.getEffectiveLevel() <= logging.DEBUG:  # if DEBUG msgs actually being logged
        dbg_trace_str = RHUtils.getFnTracebackMsgStr("build_atomic_results")
        logger.debug("Entered 'build_atomic_results()', called from: {}".format(dbg_trace_str))
        dbg_trace_str = " (called from: {})".format(dbg_trace_str)
    APP.app_context().push()
    token = monotonic()
    timing = {
        'start': token
    }

    if 'race_id' in params:
        race = rhDataObj.get_savedRaceMeta(params['race_id'])

    if 'heat_id' in params:
        heat_id = params['heat_id']
        heat = rhDataObj.get_heat(heat_id)
    elif 'race_id' in params:
        heat_id = race.heat_id
        heat = rhDataObj.get_heat(heat_id)

    if 'class_id' in params:
        class_id = params['class_id']
        USE_CLASS = True
    elif 'heat_id' in params and heat.class_id != RHUtils.CLASS_ID_NONE:
        class_id = heat.class_id
        USE_CLASS = True
    else:
        USE_CLASS = False

    # rebuild race result
    if 'race_id' in params:
        do_gevent_sleep()
        rhDataObj.clear_results_event()
        timing['race'] = monotonic()
        rhDataObj.get_results_savedRaceMeta(race)
        logger.debug('Race {} results built in {}s'.format(params['race_id'], monotonic() - timing['race']))

    # rebuild heat summary
    if 'heat_id' in params:
        do_gevent_sleep()
        rhDataObj.clear_results_event()
        timing['heat'] = monotonic()
        rhDataObj.get_results_heat(heat)
        logger.debug('Heat {} results built in {}s'.format(heat_id, monotonic() - timing['heat']))

    # rebuild class summary
    if USE_CLASS:
        do_gevent_sleep()
        rhDataObj.clear_results_event()
        timing['class'] = monotonic()
        rhDataObj.get_results_raceClass(class_id)
        logger.debug('Class {} results built in {}s'.format(class_id, monotonic() - timing['class']))

        do_gevent_sleep()
        timing['class_rank'] = monotonic()
        rhDataObj.get_ranking_raceClass(class_id)
        logger.debug('Class {} ranking built in {}s'.format(class_id, monotonic() - timing['class_rank']))

    # rebuild event summary
    do_gevent_sleep()
    timing['event'] = monotonic()
    rhDataObj.get_results_event()
    if logger.getEffectiveLevel() <= logging.DEBUG:  # if DEBUG msgs actually being logged
        logger.debug('Event results built in {}s'.format(monotonic() - timing['event']))
        logger.debug('Built result caches in {0}'.format(monotonic() - timing['start']))
        logger.debug("Exiting 'build_atomic_results()'{}".format(dbg_trace_str))

def is_in_calc_leaderboard_fn():
    return in_calc_leaderboard_fn_flag

def calc_leaderboard(racecontext, **params):
    dbg_trace_str = ""
    if logger.getEffectiveLevel() <= logging.DEBUG:  # if DEBUG msgs actually being logged
        dbg_trace_str = RHUtils.getFnTracebackMsgStr("calc_leaderboard")
        logger.debug("Entered 'calc_leaderboard()', called from: {}".format(dbg_trace_str))
        dbg_trace_str = " (called from: {})".format(dbg_trace_str)
    global in_calc_leaderboard_fn_flag
    if in_calc_leaderboard_fn_flag:
        logger.info("Waiting for previous invocation of 'calc_leaderboard()' to finish{}".format(dbg_trace_str))
        wait_count = 0
        while True:
            gevent.sleep(0.05)
            if not in_calc_leaderboard_fn_flag:
                logger.info("Previous invocation of 'calc_leaderboard()' finished; continuing{}".format(dbg_trace_str))
                break
            wait_count += 1
            if wait_count > 6000:
                logger.error("Timeout waiting for previous invocation of 'calc_leaderboard()' to finish{}".format(dbg_trace_str))
                break
    in_calc_leaderboard_fn_flag = True
    try:
        lb_result = _do_calc_leaderboard(racecontext, **params)
    finally:
        in_calc_leaderboard_fn_flag = False
    if logger.getEffectiveLevel() <= logging.DEBUG:  # if DEBUG msgs actually being logged
        logger.debug("Exiting 'calc_leaderboard()'{}".format(dbg_trace_str))
    return lb_result

def _do_calc_leaderboard(racecontext, **params):
    rhDataObj = racecontext.rhdata
    ''' Generates leaderboards '''
    meta_points_flag = False
    USE_CURRENT = False

    consecutivesCount = rhDataObj.get_optionInt('consecutivesCount', 3)
    current_heat = None
    current_class = None

    if ('current_race' in params):
        USE_CURRENT = True
        current_heat_id = params['current_race'].current_heat
        current_heat = racecontext.rhdata.get_heat(current_heat_id)
        if current_heat and current_heat.class_id:
            current_class = racecontext.rhdata.get_raceClass(current_heat.class_id)
        profile = params['current_profile']
        profile_freqs = json.loads(profile.frequencies)
        raceObj = params['current_race']
        race_format = raceObj.format

        if raceObj.current_heat:
            heat_displayname = current_heat.display_name

            if current_class:
                if current_class.format_id:
                    race_format = rhDataObj.get_raceFormat(current_class.format_id)

                if current_class.round_type == RoundType.GROUPED:
                    round_num = 0
                else:
                    round_num = racecontext.rhdata.get_round_num_for_heat(current_heat.id)
            else:
                round_num = racecontext.rhdata.get_round_num_for_heat(current_heat.id)
        else:
            heat_displayname = ''
            round_num = 0

    elif ('round_id' in params and 'heat_id' in params):
        round_id = params['round_id']
        current_heat_id = params['heat_id']
        current_heat = racecontext.rhdata.get_heat(current_heat_id)
        if current_heat.class_id:
            current_class = racecontext.rhdata.get_raceClass(current_heat.class_id)
        raceObj = rhDataObj.get_savedRaceMeta_by_heat_round(current_heat_id, round_id)
        race_format = rhDataObj.get_raceFormat(raceObj.format_id)
        heat_displayname = current_heat.display_name

        if current_class:
            if current_class.format_id:
                race_format = rhDataObj.get_raceFormat(current_class.format_id)

            if current_class.round_type == RoundType.GROUPED:
                round_num = 0
            else:
                round_num = raceObj.round_id
        else:
            round_num = raceObj.round_id

    else:
        logger.error("Invalid call to calc_leaderboard", stack_info=True)
        return False

    do_gevent_sleep()

    leaderboard = []

    # collect data for processing
    if USE_CURRENT and raceObj.current_heat == RHUtils.HEAT_ID_NONE:
        for node_index in range(raceObj.num_nodes):
            crossings = []
            laps = []

            if node_index < raceObj.num_nodes and len(raceObj.get_active_laps()):
                crossings = raceObj.get_active_laps()[node_index]

            if crossings:
                if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                    total_laps = len(crossings)
                    laps = crossings
                else:
                    total_laps = len(crossings) - 1
                    laps = crossings[1:]
            else:
                total_laps = 0

            if (profile_freqs["b"][node_index] and profile_freqs["c"][node_index]):
                callsign = profile_freqs["b"][node_index] + str(profile_freqs["c"][node_index])
            else:
                callsign = str(profile_freqs["f"][node_index])

            if profile_freqs["f"][node_index] != RHUtils.FREQUENCY_ID_NONE:
                leaderboard.append({
                    'pilot_id': None,
                    'callsign': callsign,
                    'team_name': None,
                    'laps': total_laps,
                    'starts': 1 if len(crossings) > 0 else 0,
                    'node': node_index,
                    'pilot_crossings': crossings,
                    'pilot_laps': laps,
                })
    elif USE_CURRENT:
        for pilot in rhDataObj.get_pilots():
            do_gevent_sleep(0)
            found_pilot = False
            node_index = 0
            crossings = []
            laps = []
            for node_index in raceObj.node_pilots:
                if raceObj.node_pilots[node_index] == pilot.id and node_index < raceObj.num_nodes and len(raceObj.get_active_laps()):
                    crossings = raceObj.get_active_laps()[node_index]
                    found_pilot = True
                    break

            if crossings:
                if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                    total_laps = len(crossings)
                    laps = crossings
                else:
                    total_laps = len(crossings) - 1
                    laps = crossings[1:]
            else:
                total_laps = 0

            if found_pilot and profile_freqs["f"][node_index] != RHUtils.FREQUENCY_ID_NONE:
                leaderboard.append({
                    'pilot_id': pilot.id,
                    'callsign': pilot.callsign,
                    'team_name': pilot.team,
                    'laps': total_laps,
                    'starts': 1 if len(crossings) > 0 else 0,
                    'node': node_index,
                    'pilot_crossings': crossings,
                    'pilot_laps': laps,
                })
    else:
        for pilot_race in racecontext.rhdata.get_savedPilotRaces_by_savedRaceMeta(raceObj.id):
            if pilot_race.pilot_id:
                pilot = racecontext.rhdata.get_pilot(pilot_race.pilot_id)
                pilot_laps = []
                total_laps = 0

                race_crossings = racecontext.rhdata.get_active_savedRaceLaps_by_savedPilotRace(pilot_race.id)
                total_laps += len(race_crossings)

                if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                    pilot_laps = race_crossings
                else:
                    if len(race_crossings):
                        pilot_laps = race_crossings[1:]
                        total_laps -= 1

                do_gevent_sleep(0)

                leaderboard.append({
                    'pilot_id': pilot.id,
                    'callsign': pilot.callsign,
                    'team_name': pilot.team,
                    'laps': total_laps,
                    'starts': 1 if len(race_crossings) > 0 else 0,
                    'node': pilot_race.node_index,
                    'pilot_crossings': race_crossings,
                    'pilot_laps': pilot_laps,
                })

    do_gevent_sleep()
    # find leader for each lap in race
    if USE_CURRENT:
        leader_laps = {}
        for chk_pilot in leaderboard:
            chk_laps = chk_pilot.get('pilot_crossings', [])
            for chk_lap in chk_laps:
                lnum = chk_lap.lap_number
                if lnum is not None and (lnum > 0 or (race_format and race_format.start_behavior == StartBehavior.FIRST_LAP)):
                    ldr_plt, ldr_lap = leader_laps.get(lnum, NONE_NONE_PAIR)
                    # if first entry or earliest entry for lap
                    if ldr_lap is None or chk_lap.lap_time_stamp < ldr_lap.lap_time_stamp:
                        leader_laps[lnum] = [ chk_pilot, chk_lap ]

    for result_pilot in leaderboard:
        if logger.getEffectiveLevel() <= logging.DEBUG:  # if DEBUG msgs actually being logged
            logger.debug("Calculating leaderboard data for pilot_id {}".format(result_pilot.get('pilot_id', -1)))
        do_gevent_sleep()

        # Get the total race time for each pilot
        l_time_total = 0
        for lap in result_pilot['pilot_crossings']:
            l_time_total += lap.lap_time
        result_pilot['total_time'] = round(l_time_total, 3)

        if len(result_pilot['pilot_crossings']) != len(result_pilot['pilot_laps']):
            l_time_total -= result_pilot['pilot_crossings'][0].lap_time
        result_pilot['total_time_laps'] = round(l_time_total, 3)

        if result_pilot['laps']:
            # Get the last lap for each pilot
            result_pilot['last_lap'] = result_pilot['pilot_laps'][-1].lap_time
            # Get the average lap time for each pilot
            result_pilot['average_lap'] = round(result_pilot['total_time_laps'] / result_pilot['laps'], 3)
            # Get the fastest lap time for each pilot
            result_pilot['fastest_lap'] = sorted(result_pilot['pilot_laps'], key=lambda val: val.lap_time)[0].lap_time
            # Set lap source info
            source = {
                'round': round_num,
                'heat': current_heat_id,
                'displayname': heat_displayname,
            }

            do_gevent_sleep(0)

            # Determine number of seconds behind leader
            result_pilot['time_behind'] = None
            if USE_CURRENT:
                current_lap = result_pilot['pilot_laps'][-1]
                cur_lap_num = current_lap.lap_number
                # check if pilot has completed at least first lap
                if cur_lap_num > 0 or \
                        (race_format and race_format.start_behavior == StartBehavior.FIRST_LAP):
                    ldr_pilot, ldr_lap = leader_laps.get(cur_lap_num, NONE_NONE_PAIR)
                    # if another pilot is leader on lap
                    if ldr_lap is not None and ldr_pilot.get('node') != result_pilot.get('node'):
                        ldr_lap_ts = ldr_lap.lap_time_stamp
                        cur_lap_ts = current_lap.lap_time_stamp
                        if cur_lap_ts > ldr_lap_ts:
                            result_pilot['time_behind'] = round(cur_lap_ts - ldr_lap_ts, 3)

                do_gevent_sleep(0)

            # find best consecutive X laps
            all_consecutives = []

            if result_pilot['laps'] >= consecutivesCount:
                for i in range(result_pilot['laps'] - (consecutivesCount - 1)):
                    do_gevent_sleep(0)
                    all_consecutives.append({
                        'laps': consecutivesCount,
                        'time': sum([data.lap_time for data in result_pilot['pilot_laps'][i : i + consecutivesCount]]),
                        'lap_index': i+1
                    })
            else:
                all_consecutives.append({
                    'laps': result_pilot['laps'],
                    'time': result_pilot['total_time_laps'],
                    'lap_index': None
                })

            do_gevent_sleep(0)

            # Sort consecutives
            all_consecutives.sort(key = lambda x: (-x['laps'], not bool(x['time']), x['time']))

            result_pilot['consecutives'] = round(all_consecutives[0]['time'], 3)
            result_pilot['consecutives_base'] = all_consecutives[0]['laps']
            result_pilot['consecutive_lap_start'] = all_consecutives[0]['lap_index']

        else:
            result_pilot['last_lap'] = None
            result_pilot['average_lap'] = 0
            result_pilot['fastest_lap'] = 0
            source = None
            result_pilot['time_behind'] = None
            result_pilot['consecutives'] = None
            result_pilot['consecutives_base'] = 0
            result_pilot['consecutive_lap_start'] = None

        result_pilot['fastest_lap_source'] = source
        result_pilot['consecutives_source'] = source

    do_gevent_sleep()

    # Combine leaderboard
    for result_pilot in leaderboard:
        # Clean up interim data
        result_pilot.pop('pilot_crossings')
        result_pilot.pop('pilot_laps')

        # shift output keys
        result_pilot['total_time_raw'] = result_pilot['total_time']
        result_pilot['total_time_laps_raw'] = result_pilot['total_time_laps']
        result_pilot['average_lap_raw'] = result_pilot['average_lap']
        result_pilot['fastest_lap_raw'] = result_pilot['fastest_lap']
        result_pilot['time_behind_raw'] = result_pilot['time_behind']
        result_pilot['consecutives_raw'] = result_pilot['consecutives']
        result_pilot['last_lap_raw'] = result_pilot['last_lap']

        if race_format and race_format.start_behavior == StartBehavior.STAGGERED:
            result_pilot['total_time_raw'] = result_pilot['total_time_laps_raw']

    leaderboard_output = {
        'by_race_time': copy.deepcopy(leaderboard),
        'by_fastest_lap': copy.deepcopy(leaderboard),
        'by_consecutives': copy.deepcopy(leaderboard)
    }

    if race_format and race_format.win_condition == WinCondition.FASTEST_CONSECUTIVE:
        primary_leaderboard = 'by_consecutives'
    elif race_format and race_format.win_condition == WinCondition.FASTEST_LAP:
        primary_leaderboard = 'by_fastest_lap'
    else:
        # WinCondition.NONE
        # WinCondition.MOST_LAPS
        # WinCondition.FIRST_TO_LAP_X
        primary_leaderboard = 'by_race_time'

    leaderboard_output['meta'] = {
        'primary_leaderboard': primary_leaderboard,
        'win_condition': race_format.win_condition if race_format else None,
        'team_racing_mode': race_format.team_racing_mode if race_format else False,
        'start_behavior': race_format.start_behavior if race_format else None,
        'consecutives_count': consecutivesCount,
    }

    if meta_points_flag:
        leaderboard_output['meta']['primary_points'] = True

    leaderboard_output = sort_and_rank_leaderboards(racecontext, leaderboard_output)
    leaderboard_output = format_leaderboard_times(racecontext, leaderboard_output)
    leaderboard_output = add_fastest_race_lap_meta(racecontext, leaderboard_output)

    return leaderboard_output

def format_leaderboard_times(racecontext, all_leaderboards):
    time_format = racecontext.serverconfig.get_item('UI', 'timeFormat')
    for key, leaderboard in all_leaderboards.items():
        if key != 'meta':
            for result_pilot in leaderboard:
                result_pilot['total_time'] = RHUtils.format_time_to_str(result_pilot['total_time_raw'], time_format)
                result_pilot['total_time_laps'] = RHUtils.format_time_to_str(result_pilot['total_time_laps_raw'], time_format)
                result_pilot['average_lap'] = RHUtils.format_time_to_str(result_pilot['average_lap_raw'], time_format)
                result_pilot['fastest_lap'] = RHUtils.format_time_to_str(result_pilot['fastest_lap_raw'], time_format)
                if result_pilot.get('time_behind_raw'):
                    result_pilot['time_behind'] = RHUtils.format_time_to_str(result_pilot['time_behind_raw'], time_format)
                else:
                    result_pilot.pop('time_behind', None)
                    result_pilot.pop('time_behind_raw', None)
                result_pilot['consecutives'] = RHUtils.format_time_to_str(result_pilot['consecutives_raw'], time_format)
                if result_pilot.get('last_lap_raw'):
                    result_pilot['last_lap'] = RHUtils.format_time_to_str(result_pilot['last_lap_raw'], time_format)

    return all_leaderboards

def sort_and_rank_leaderboards(racecontext, all_leaderboards):
    consecutivesCount = all_leaderboards['meta']['consecutives_count']

    # Sort by race time
    all_leaderboards['by_race_time'] = sorted(all_leaderboards['by_race_time'], key=lambda x: (
        -x['laps'],  # reverse lap count
        x['total_time_raw'] if x['total_time_raw'] and x['total_time_raw'] > 0 else float('inf')
    # total time ascending except 0
    ))

    # determine ranking
    last_rank = None
    last_rank_laps = 0
    last_rank_time = 0
    for i, row in enumerate(all_leaderboards['by_race_time'], start=1):
        if not row['total_time_raw']:
            pos = None
        else:
            pos = i
            if last_rank_laps == row['laps'] and last_rank_time == row['total_time_raw']:
                pos = last_rank
        last_rank = pos
        last_rank_laps = row['laps']
        last_rank_time = row['total_time_raw']

        row['position'] = pos
        row['behind'] = all_leaderboards['by_race_time'][0]['laps'] - row['laps']

    do_gevent_sleep()
    # Sort by fastest laps
    all_leaderboards['by_fastest_lap'] = sorted(all_leaderboards['by_fastest_lap'], key=lambda x: (
        x['fastest_lap_raw'] if x['fastest_lap_raw'] and x['fastest_lap_raw'] > 0 else float('inf'),  # fastest lap
        x['total_time_raw'] if x['total_time_raw'] and x['total_time_raw'] > 0 else float('inf')  # total time
    ))

    # determine ranking
    last_rank = None
    last_rank_fastest_lap = 0
    for i, row in enumerate(all_leaderboards['by_fastest_lap'], start=1):
        if not row['total_time_raw']:
            pos = None
        else:
            pos = i
            if last_rank_fastest_lap == row['fastest_lap_raw']:
                pos = last_rank
        last_rank = pos
        last_rank_fastest_lap = row['fastest_lap_raw']

        row['position'] = pos

    do_gevent_sleep()
    # Sort by consecutive laps
    all_leaderboards['by_consecutives'] = sorted(all_leaderboards['by_consecutives'], key=lambda x: (
        -x['consecutives_base'] if x['consecutives_base'] else 0,
        x['consecutives_raw'] if x['consecutives_raw'] and x['consecutives_raw'] > 0 else float('inf'),  # fastest consecutives
        -x['laps'],  # reverse lap count
        x['total_time_raw'] if x['total_time_raw'] and x['total_time_raw'] > 0 else float('inf')
    ))

    # determine ranking
    last_rank = None
    last_rank_laps = 0
    last_rank_time = 0
    last_rank_consecutive = None
    for i, row in enumerate(all_leaderboards['by_consecutives'], start=1):
        if not row['total_time_raw']:
            pos = None
        else:
            pos = i
            if last_rank_consecutive == row['consecutives_raw']:
                if row['laps'] < consecutivesCount:
                    if last_rank_laps == row['laps'] and last_rank_time == row['total_time_raw']:
                        pos = last_rank
                else:
                    pos = last_rank
        last_rank = pos
        last_rank_laps = row['laps']
        last_rank_time = row['total_time_raw']
        last_rank_consecutive = row['consecutives_raw']

        row['position'] = pos

    return racecontext.filters.run_filters(Flt.LEADERBOARD_SORT_AND_RANK, all_leaderboards)

def refresh_source_displayname(racecontext, result, heat_id):
    for key, leaderboard in result.items():
        if key != 'meta':
            for result_pilot in leaderboard:
                if result_pilot['fastest_lap_source'] and result_pilot['fastest_lap_source']['heat'] == heat_id:
                    fl_heat = result_pilot['fastest_lap_source']['heat']
                    fl_name = racecontext.rhdata.get_heat(fl_heat).display_name
                    result_pilot['fastest_lap_source']['displayname'] = fl_name

                if result_pilot['consecutives_source'] and result_pilot['consecutives_source']['heat'] == heat_id:
                    cons_heat = result_pilot['consecutives_source']['heat']
                    cons_name = racecontext.rhdata.get_heat(cons_heat).display_name
                    result_pilot['consecutives_source']['displayname'] = cons_name
    return result

def add_fastest_race_lap_meta(racecontext, all_leaderboards):
    # fetch pilot/time data for fastest lap in race
    leaderboard_by_fastest_lap = all_leaderboards['by_fastest_lap']
    fastest_race_lap_data = None
    if len(leaderboard_by_fastest_lap) > 0 and leaderboard_by_fastest_lap[0]['laps'] > 0:
        if all_leaderboards['meta'].get('fastest_race_lap_data'):
            if all_leaderboards['meta']['fastest_race_lap_data']['text'][1] == [leaderboard_by_fastest_lap[0]['callsign'],
                                                                                leaderboard_by_fastest_lap[0]['fastest_lap']]:
                return all_leaderboards # no change
        else:
            pilot = racecontext.rhdata.get_pilot(leaderboard_by_fastest_lap[0]['pilot_id'])
            pilot_str = pilot.spoken_callsign if pilot else leaderboard_by_fastest_lap[0]['callsign']
            phonetic_time = RHUtils.format_phonetic_time_to_str(
                leaderboard_by_fastest_lap[0]['fastest_lap_raw'],
                racecontext.serverconfig.get_item('UI', 'timeFormatPhonetic'))
            fastest_race_lap_data = {}
            fastest_race_lap_data['phonetic'] = [pilot_str, phonetic_time]
            fastest_race_lap_data['text'] = [leaderboard_by_fastest_lap[0]['callsign'],
                                             leaderboard_by_fastest_lap[0]['fastest_lap']]

    all_leaderboards['meta']['fastest_race_lap_data'] = fastest_race_lap_data

    return all_leaderboards

def build_leaderboard_race(racecontext, heat_id, round_id):
    result = calc_leaderboard(racecontext, heat_id=heat_id, round_id=round_id)
    return racecontext.filters.run_filters(Flt.LEADERBOARD_BUILD_RACE, result)

def build_leaderboard_heat(racecontext, heat):
    leaderboard = {}
    races = racecontext.rhdata.get_savedRaceMetas_by_heat(heat.id)
    for race in races:
        race_result = racecontext.rhdata.get_results_savedRaceMeta(race)
        leaderboard = build_incremental(racecontext, race_result, leaderboard, transient=True)

    leaderboard = format_leaderboard_times(racecontext, leaderboard)
    leaderboard = sort_and_rank_leaderboards(racecontext, leaderboard)
    leaderboard = add_fastest_race_lap_meta(racecontext, leaderboard)

    return racecontext.filters.run_filters(Flt.LEADERBOARD_BUILD_HEAT, leaderboard)

def build_leaderboard_class(racecontext, race_class):
    leaderboard = {}
    heats = racecontext.rhdata.get_heats_by_class(race_class.id)
    for heat in heats:
        heat_result = racecontext.rhdata.get_results_heat(heat)
        leaderboard = build_incremental(racecontext, heat_result, leaderboard, transient=True)

    leaderboard = format_leaderboard_times(racecontext, leaderboard)
    leaderboard = sort_and_rank_leaderboards(racecontext, leaderboard)
    leaderboard = add_fastest_race_lap_meta(racecontext, leaderboard)

    return racecontext.filters.run_filters(Flt.LEADERBOARD_BUILD_CLASS, leaderboard)

def build_leaderboard_event(racecontext):
    leaderboard = {}
    all_classes = racecontext.rhdata.get_raceClasses()
    for race_class in all_classes:
        class_result = racecontext.rhdata.get_results_raceClass(race_class)
        leaderboard = build_incremental(racecontext, class_result, leaderboard, transient=True)

    unclassified_heats = racecontext.rhdata.get_heats_by_class(RHUtils.CLASS_ID_NONE)
    for heat in unclassified_heats:
        heat_result = racecontext.rhdata.get_results_heat(heat)
        leaderboard = build_incremental(racecontext, heat_result, leaderboard, transient=True)

    leaderboard = format_leaderboard_times(racecontext, leaderboard)
    leaderboard = sort_and_rank_leaderboards(racecontext, leaderboard)
    leaderboard = add_fastest_race_lap_meta(racecontext, leaderboard)

    return racecontext.filters.run_filters(Flt.LEADERBOARD_BUILD_EVENT, leaderboard)

def build_incremental(racecontext, merge_input, source_input, transient=False):
    merge_result = copy.deepcopy(merge_input)
    source_result = copy.deepcopy(source_input)

    if not source_result:
        return merge_result

    if not merge_result:
        return source_result

    output_result = {}
    for key, value in source_result.items():
        output_result[key] = value
        if key == 'meta':
            output_result['meta'].pop('fastest_race_lap_data', None)
            for meta_key, source_meta_value in output_result['meta'].items():
                if merge_result['meta'].get(meta_key) and merge_result['meta'][meta_key] != source_meta_value:
                    if meta_key == 'primary_leaderboard':
                        output_result['meta']['primary_leaderboard'] = 'by_race_time'
                    elif meta_key == 'win_condition':
                        output_result['meta']['win_condition'] = WinCondition.NONE
                    elif meta_key == 'team_racing_mode':
                        output_result['meta']['team_racing_mode'] = False
                    elif meta_key == 'start_behavior':
                        output_result['meta']['start_behavior'] = None
                    elif meta_key == 'consecutives_count':
                        output_result['meta']['consecutives_count'] = racecontext.rhdata.get_optionInt('consecutivesCount', 3)
                    elif meta_key == 'primary_points':
                        output_result['meta']['primary_points'] = False

        else:
            for lb_line in merge_result[key]:
                for idx, item in enumerate(source_result[key]):
                    if item['pilot_id'] == lb_line['pilot_id']:
                        # simple incremental adds
                        race_result_updates = {
                            'laps': item['laps'] + lb_line['laps'],
                            'starts': item['starts'] + lb_line['starts'],
                            'total_time_raw': item['total_time_raw'] + lb_line['total_time_raw'],
                            'total_time_laps_raw': item['total_time_laps_raw'] + lb_line['total_time_laps_raw'],
                            'points': (item['points'] if 'points' in item else 0) + (lb_line['points'] if 'points' in lb_line else 0)
                        }

                        # average lap
                        if race_result_updates['laps']:
                            race_result_updates['average_lap_raw'] = race_result_updates['total_time_laps_raw'] / race_result_updates['laps']

                        # fastest lap & source
                        if not item['fastest_lap_raw'] or (lb_line['fastest_lap_raw'] and lb_line['fastest_lap_raw'] < item['fastest_lap_raw']):
                            race_result_updates['fastest_lap_raw'] = lb_line['fastest_lap_raw']
                            race_result_updates['fastest_lap_source'] = lb_line['fastest_lap_source']

                        # consecutives & source
                        if lb_line['consecutives_base'] and \
                            ( lb_line['consecutives_base'] > item['consecutives_base'] or \
                              ( lb_line['consecutives_base'] == item['consecutives_base'] and \
                              lb_line['consecutives_raw'] < item['consecutives_raw']) \
                            ):
                            race_result_updates['consecutives_base'] = lb_line['consecutives_base']
                            race_result_updates['consecutives_raw'] = lb_line['consecutives_raw']
                            race_result_updates['consecutive_lap_start'] = lb_line['consecutive_lap_start']
                            race_result_updates['consecutives_source'] = lb_line['consecutives_source']

                        output_result[key][idx].update(race_result_updates)
                        output_result[key][idx].pop('time_behind', None)
                        output_result[key][idx].pop('time_behind_raw', None)
                        break
                else:
                    # no match, make new line
                    output_result[key].append(lb_line)

    #re-sort lbs
    if not transient:
        output_result = format_leaderboard_times(racecontext, output_result)
        output_result = sort_and_rank_leaderboards(racecontext, output_result)
        output_result = add_fastest_race_lap_meta(racecontext, output_result)

    return racecontext.filters.run_filters(Flt.LEADERBOARD_BUILD_INCREMENTAL, output_result)


def calc_team_leaderboard(racecontext):
    '''Calculates and returns team-racing info.'''
    raceObj = racecontext.race
    rhDataObj = racecontext.rhdata
    time_format = racecontext.serverconfig.get_item('UI', 'timeFormat')
    # Uses current results cache / requires calc_leaderboard to have been run prior
    race_format = raceObj.format
    consecutivesCount = rhDataObj.get_optionInt('consecutivesCount', 3)

    if raceObj.results:
        results = raceObj.results['by_race_time']

        teams = {}

        for line in results:
            contributing = 0
            if race_format and race_format.win_condition == WinCondition.FASTEST_CONSECUTIVE:
                if line['laps'] >= consecutivesCount:
                    contributing = 1
            else:
                # race_format.win_condition == WinCondition.MOST_LAPS or \
                # race_format.win_condition == WinCondition.FIRST_TO_LAP_X or \
                # race_format.win_condition == WinCondition.FASTEST_LAP:
                if line['laps'] > 0:
                    contributing = 1

            if line['team_name'] in teams:
                teams[line['team_name']]['contributing'] += contributing
                teams[line['team_name']]['members'] += 1
                teams[line['team_name']]['laps'] += line['laps']
                teams[line['team_name']]['total_time_raw'] += line['total_time_raw']
                if line['average_lap_raw']:
                    teams[line['team_name']]['combined_average_lap_raw'] += line['average_lap_raw']
                if line['fastest_lap_raw']:
                    teams[line['team_name']]['combined_fastest_lap_raw'] += line['fastest_lap_raw']
                if line['consecutives_raw'] and line['consecutives_base'] >= consecutivesCount:
                    teams[line['team_name']]['combined_consecutives_raw'] += line['consecutives_raw']

            else:
                teams[line['team_name']] = {}
                teams[line['team_name']]['contributing'] = contributing
                teams[line['team_name']]['members'] = 1
                teams[line['team_name']]['laps'] = line['laps']
                teams[line['team_name']]['total_time_raw'] = line['total_time_raw']
                teams[line['team_name']]['combined_average_lap_raw'] = line['average_lap_raw']
                teams[line['team_name']]['combined_fastest_lap_raw'] = line['fastest_lap_raw']
                teams[line['team_name']]['combined_consecutives_raw'] = line['consecutives_raw']

        # convert dict to list
        leaderboard = []
        for team in teams:
            contribution_amt = float(teams[team]['contributing']) / teams[team]['members']
            average_lap_raw = 0
            average_fastest_lap_raw = 0
            average_consecutives_raw = 0
            if teams[team]['contributing']:
                if teams[team]['combined_average_lap_raw']:
                    average_lap_raw = round(float(teams[team]['combined_average_lap_raw']) / teams[team]['contributing'], 3)

                if teams[team]['combined_fastest_lap_raw']:
                    average_fastest_lap_raw = round(float(teams[team]['combined_fastest_lap_raw']) / teams[team]['contributing'], 3)

                if teams[team]['combined_consecutives_raw']:
                    average_consecutives_raw = round(float(teams[team]['combined_consecutives_raw']) / teams[team]['contributing'], 3)
            teams[team]['total_time_raw'] = round(teams[team]['total_time_raw'], 3)

            leaderboard.append({
                'name': team,
                'contributing': teams[team]['contributing'],
                'members': teams[team]['members'],
                'contribution_amt': contribution_amt,
                'laps': teams[team]['laps'],
                'total_time_raw': teams[team]['total_time_raw'],
                'average_lap_raw': average_lap_raw,
                'average_fastest_lap_raw': average_fastest_lap_raw,
                'average_consecutives_raw': average_consecutives_raw,
                'total_time': RHUtils.format_time_to_str(teams[team]['total_time_raw'], time_format),
                'average_lap': RHUtils.format_time_to_str(average_lap_raw, time_format),
                'average_fastest_lap': RHUtils.format_time_to_str(average_fastest_lap_raw, time_format),
                'average_consecutives': RHUtils.format_time_to_str(average_consecutives_raw, time_format),
            })

        # sort race_time
        leaderboard_by_race_time = copy.deepcopy(sorted(leaderboard, key = lambda x: (
            -x['laps'],
            x['average_lap_raw'] if x['average_lap_raw'] > 0 else float('inf'),
        )))

        # determine ranking
        last_rank = None
        last_rank_laps = 0
        last_rank_time = 0
        for i, row in enumerate(leaderboard_by_race_time, start=1):
            pos = i
            if last_rank_laps == row['laps'] and last_rank_time == row['average_lap_raw']:
                pos = last_rank
            last_rank = pos
            last_rank_laps = row['laps']
            last_rank_time = row['average_lap_raw']
            row['position'] = pos

        # sort fastest lap
        leaderboard_by_fastest_lap = copy.deepcopy(sorted(leaderboard, key = lambda x: (
            -x['contribution_amt'],
            x['average_fastest_lap_raw'] if x['average_fastest_lap_raw'] > 0 else float('inf'),
            -x['laps'],
        )))

        # determine ranking
        last_rank = None
        last_rank_contribution_amt = 0
        last_rank_fastest_lap = 0
        for i, row in enumerate(leaderboard_by_fastest_lap, start=1):
            pos = i
            if row['contribution_amt'] == last_rank_contribution_amt:
                if last_rank_fastest_lap == row['average_fastest_lap_raw']:
                    pos = last_rank
            last_rank = pos
            last_rank_fastest_lap = row['average_fastest_lap_raw']
            row['position'] = pos

        # sort consecutives
        leaderboard_by_consecutives = copy.deepcopy(sorted(leaderboard, key = lambda x: (
            -x['contribution_amt'],
            x['average_consecutives_raw'] if x['average_consecutives_raw'] > 0 else float('inf'),
            -x['laps'],
        )))

        # determine ranking
        last_rank = None
        last_rank_contribution_amt = 0
        last_rank_laps = 0
        last_rank_time = 0
        last_rank_consecutive = 0
        for i, row in enumerate(leaderboard_by_consecutives, start=1):
            pos = i
            if row['contribution_amt'] == last_rank_contribution_amt:
                if last_rank_consecutive == row['average_consecutives_raw']:
                    if row['laps'] < consecutivesCount:
                        if last_rank_laps == row['laps'] and last_rank_time == row['total_time_raw']:
                            pos = last_rank
                    else:
                        pos = last_rank
            last_rank = pos
            last_rank_laps = row['laps']
            last_rank_time = row['total_time_raw']
            last_rank_consecutive = row['average_consecutives_raw']
            row['position'] = pos

        leaderboard_output = {
            'by_race_time': leaderboard_by_race_time,
            'by_avg_fastest_lap': leaderboard_by_fastest_lap,
            'by_avg_consecutives': leaderboard_by_consecutives
        }

        if race_format:
            if race_format.win_condition == WinCondition.FASTEST_CONSECUTIVE:
                primary_leaderboard = 'by_avg_consecutives'
            elif race_format.win_condition == WinCondition.FASTEST_LAP:
                primary_leaderboard = 'by_avg_fastest_lap'
            else:
                # WinCondition.NONE
                # WinCondition.MOST_LAPS
                # WinCondition.FIRST_TO_LAP_X
                primary_leaderboard = 'by_race_time'

            leaderboard_output['meta'] = {
                'primary_leaderboard': primary_leaderboard,
                'win_condition': race_format.win_condition,
                'teams': teams
            }
        else:
            leaderboard_output['meta'] = {
                'primary_leaderboard': 'by_race_time',
                'win_condition': WinCondition.NONE,
                'teams': teams
            }

        return leaderboard_output
    return None

def calc_coop_leaderboard(racecontext):
    '''Calculates and returns co-op-racing info.'''
    raceObj = racecontext.race
    time_format = racecontext.serverconfig.get_item('UI', 'timeFormat')
    # Uses current results cache / requires calc_leaderboard to have been run prior
    race_format = raceObj.format

    if raceObj.results:
        results = raceObj.results['by_race_time']

        coopGroup = {}

        for line in results:
            contributing = 0
            if race_format and race_format.win_condition == WinCondition.FASTEST_CONSECUTIVE:
                if line['laps'] >= 3:
                    contributing = 1
            else:
                # race_format.win_condition == WinCondition.MOST_LAPS or \
                # race_format.win_condition == WinCondition.FIRST_TO_LAP_X or \
                # race_format.win_condition == WinCondition.FASTEST_LAP:
                if line['laps'] > 0:
                    contributing = 1

            if coopGroup:
                coopGroup['contributing'] += contributing
                coopGroup['members'] += 1
                coopGroup['laps'] += line['laps']
                coopGroup['total_time_raw'] += line['total_time_raw']
                if line['total_time_raw'] > coopGroup['coop_total_time_raw']:
                    coopGroup['coop_total_time_raw'] = line['total_time_raw']  # track last lap
                    coopGroup['coop_total_time'] = line['total_time']
                if line['average_lap_raw']:
                    coopGroup['combined_average_lap_raw'] += line['average_lap_raw']
                if line['fastest_lap_raw']:
                    coopGroup['combined_fastest_lap_raw'] += line['fastest_lap_raw']
                if line['consecutives_raw']:
                    coopGroup['combined_consecutives_raw'] += line['consecutives_raw']
            else:
                coopGroup['contributing'] = contributing
                coopGroup['members'] = 1
                coopGroup['laps'] = line['laps']
                coopGroup['total_time_raw'] = line['total_time_raw']
                coopGroup['coop_total_time_raw'] = line['total_time_raw']
                coopGroup['coop_total_time'] = line['total_time']
                coopGroup['combined_average_lap_raw'] = line['average_lap_raw']
                coopGroup['combined_fastest_lap_raw'] = line['fastest_lap_raw']
                coopGroup['combined_consecutives_raw'] = line['consecutives_raw']

        contribution_amt = 0
        average_lap_raw = 0
        average_fastest_lap_raw = 0
        average_consecutives_raw = 0
        if coopGroup['contributing']:
            if coopGroup['members']:
                contribution_amt = float(coopGroup['contributing']) / coopGroup['members']
            if coopGroup['combined_average_lap_raw']:
                average_lap_raw = round(float(coopGroup['combined_average_lap_raw']) / coopGroup['contributing'], 3)
            if coopGroup['combined_fastest_lap_raw']:
                average_fastest_lap_raw = round(float(coopGroup['combined_fastest_lap_raw']) / coopGroup['contributing'], 3)
            if coopGroup['combined_consecutives_raw']:
                average_consecutives_raw = round(float(coopGroup['combined_consecutives_raw']) / coopGroup['contributing'], 3)
        coopGroup['coop_total_time_raw'] = round(coopGroup['coop_total_time_raw'], 3)

        leaderboard = [{
            'name': "Group",
            'contributing': coopGroup['contributing'],
            'members': coopGroup['members'],
            'contribution_amt': contribution_amt,
            'laps': coopGroup['laps'],
            'total_time_raw': coopGroup['total_time_raw'],
            'coop_total_time_raw': coopGroup['coop_total_time_raw'],
            'coop_total_time': coopGroup['coop_total_time'],
            'average_lap_raw': average_lap_raw,
            'average_fastest_lap_raw': average_fastest_lap_raw,
            'average_consecutives_raw': average_consecutives_raw,
            'total_time': RHUtils.format_time_to_str(coopGroup['total_time_raw'], time_format),
            'average_lap': RHUtils.format_time_to_str(average_lap_raw, time_format),
            'average_fastest_lap': RHUtils.format_time_to_str(average_fastest_lap_raw, time_format),
            'average_consecutives': RHUtils.format_time_to_str(average_consecutives_raw, time_format),
        }]

        leaderboard_output = {
            'by_race_time': leaderboard
        }

        if race_format:
            if race_format.win_condition == WinCondition.FASTEST_CONSECUTIVE:
                primary_leaderboard = 'by_avg_consecutives'
            elif race_format.win_condition == WinCondition.FASTEST_LAP:
                primary_leaderboard = 'by_avg_fastest_lap'
            else:
                # WinCondition.NONE
                # WinCondition.MOST_LAPS
                # WinCondition.FIRST_TO_LAP_X
                primary_leaderboard = 'by_race_time'

            leaderboard_output['meta'] = {
                'primary_leaderboard': primary_leaderboard,
                'win_condition': race_format.win_condition,
                'coopGroup': coopGroup
            }
        else:
            leaderboard_output['meta'] = {
                'primary_leaderboard': 'by_race_time',
                'win_condition': WinCondition.NONE,
                'coopGroup': coopGroup
            }

        return leaderboard_output
    return None

def calc_class_ranking_leaderboard(racecontext, race_class=None, class_id=None):
    if class_id:
        race_class = racecontext.rhdata.get_raceClass(class_id)

    if race_class:
        args = json.loads(race_class.rank_settings) if race_class.rank_settings else None
        if race_class.win_condition in racecontext.raceclass_rank_manager.methods:
            ranking, meta = racecontext.raceclass_rank_manager.rank(race_class.win_condition, race_class, args)
            return {
                'ranking': ranking,
                'meta': meta
            }
        elif race_class.win_condition:
            logger.warning("{} uses unsupported ranking method: {}".format(race_class.display_name, race_class.win_condition))

    return False

def get_gap_info(racecontext, seat_index):
    ''' Assembles current lap information for OSD '''

    # select correct results
    win_condition = racecontext.race.format.win_condition
    consecutivesCount = racecontext.rhdata.get_optionInt('consecutivesCount', 3)

    if win_condition == WinCondition.FASTEST_CONSECUTIVE:
        leaderboard = racecontext.race.results['by_consecutives']
    elif win_condition == WinCondition.FASTEST_LAP:
        leaderboard = racecontext.race.results['by_fastest_lap']
    else:
        # WinCondition.MOST_LAPS
        # WinCondition.FIRST_TO_LAP_X
        # WinCondition.NONE
        leaderboard = racecontext.race.results['by_race_time']

    # get this seat's results
    result = None
    for index, result in enumerate(leaderboard):
        if result['node'] == seat_index:
            rank_index = index
            break
    else: # no break
        logger.error('Failed to find results: Node not in result list')
        return

    # check for best lap
    is_best_lap = False
    if result['fastest_lap_raw'] == result['last_lap_raw']:
        is_best_lap = True

    # get the next faster results
    next_rank_split = None
    next_rank_split_result = None
    if isinstance(result['position'], int) and result['position'] > 1:
        next_rank_split_result = leaderboard[rank_index - 1]

        if next_rank_split_result['total_time_raw']:
            if win_condition == WinCondition.FASTEST_CONSECUTIVE:
                if next_rank_split_result['consecutives_raw'] and next_rank_split_result['consecutives_base'] == consecutivesCount:
                    next_rank_split = result['consecutives_raw'] - next_rank_split_result['consecutives_raw']
            elif win_condition == WinCondition.FASTEST_LAP:
                if next_rank_split_result['fastest_lap_raw']:
                    next_rank_split = result['last_lap_raw'] or 0 - next_rank_split_result['fastest_lap_raw']
            else:
                # WinCondition.MOST_LAPS
                # WinCondition.FIRST_TO_LAP_X
                next_rank_split = result['total_time_raw'] - next_rank_split_result['total_time_raw']
    else:
        # check split to self
        next_rank_split_result = leaderboard[rank_index]

        if win_condition == WinCondition.FASTEST_CONSECUTIVE or win_condition == WinCondition.FASTEST_LAP:
            if next_rank_split_result['fastest_lap_raw']:
                if result['last_lap_raw'] > next_rank_split_result['fastest_lap_raw']:
                    next_rank_split = result['last_lap_raw'] - next_rank_split_result['fastest_lap_raw']

    # get the fastest result
    first_rank_split = None
    first_rank_split_result = None
    if isinstance(result['position'], int) and result['position'] > 2:
        first_rank_split_result = leaderboard[0]

        if first_rank_split_result['total_time_raw']:
            if win_condition == WinCondition.FASTEST_CONSECUTIVE and result['consecutives_base'] == consecutivesCount:
                if first_rank_split_result['consecutives_raw']:
                    first_rank_split = result['consecutives_raw'] - first_rank_split_result['consecutives_raw']
            elif win_condition == WinCondition.FASTEST_LAP:
                if first_rank_split_result['fastest_lap_raw']:
                    first_rank_split = result['last_lap_raw'] or 0 - first_rank_split_result['fastest_lap_raw']
            else:
                # WinCondition.MOST_LAPS
                # WinCondition.FIRST_TO_LAP_X
                first_rank_split = result['total_time_raw'] - first_rank_split_result['total_time_raw']

    # Set up output objects

    pass_info = LapInfo()

    # Race
    #TODO pass_info.race.total_pilots = None
    #TODO pass_info.race.lap_max = None
    pass_info.race.consecutives_base = consecutivesCount
    pass_info.race.win_condition = win_condition
    #TODO pass_info.race.best_lap = None
    #TODO pass_info.race.best_lap_callsign = None
    #TODO pass_info.race.split_count = None

    # Current pilot
    pass_info.current.lap_list = racecontext.race.get_lap_results()['node_index'][seat_index]

    pass_info.current.pilot_id = result['pilot_id']
    pass_info.current.seat = int(seat_index)
    pass_info.current.position = int(result['position'] or 0)
    pass_info.current.callsign = str(result['callsign'])
    pass_info.current.lap_number = None
    pass_info.current.last_lap_time = None
    pass_info.current.total_time = int(round(result['total_time_raw'], 0))
    pass_info.current.total_time_laps = int(round(result['total_time_laps_raw'], 0))
    pass_info.current.consecutives = None
    pass_info.current.is_best_lap = bool(is_best_lap)

    if result['laps']:
        pass_info.current.lap_number = result['laps']
        pass_info.current.last_lap_time = int(round(result['last_lap_raw'], 0))
    else:
        pass_info.current.lap_number = 0
        pass_info.current.last_lap_time = int(round(result['total_time_raw'], 0))
        pass_info.current.is_best_lap = False

    if result['consecutives']:
        pass_info.current.consecutives = int(round(result['consecutives_raw'], 0))
        pass_info.current.consecutives_base = int(round(result['consecutives_base'], 0))

    # Next faster pilot
    if next_rank_split:
        pass_info.next_rank.pilot_id = next_rank_split_result['pilot_id']
        pass_info.next_rank.seat = int(next_rank_split_result['node'])
        pass_info.next_rank.position = None
        pass_info.next_rank.callsign = str(next_rank_split_result['callsign'])
        pass_info.next_rank.diff_time = int(round(next_rank_split, 0 ))
        pass_info.next_rank.lap_number = next_rank_split_result['laps']
        pass_info.next_rank.last_lap_time = None
        pass_info.next_rank.total_time = int(round(next_rank_split_result['total_time_raw'], 0))

        if next_rank_split_result['position']:
            pass_info.next_rank.position = int(next_rank_split_result['position'])

            if next_rank_split_result['laps'] < 1:
                pass_info.next_rank.last_lap_time = int(round(next_rank_split_result['total_time_raw'], 0))
            else:
                pass_info.next_rank.last_lap_time = int(round(next_rank_split_result['last_lap_raw'], 0))

    # Race Leader
    if first_rank_split:
        pass_info.first_rank.pilot_id = first_rank_split_result['pilot_id']
        pass_info.first_rank.seat = int(first_rank_split_result['node'])
        pass_info.first_rank.position = None
        pass_info.first_rank.callsign = str(first_rank_split_result['callsign'])
        pass_info.first_rank.diff_time = int(round(first_rank_split, 0))
        pass_info.first_rank.lap_number = first_rank_split_result['laps']
        pass_info.first_rank.last_lap_time = None
        pass_info.first_rank.total_time = int(round(first_rank_split_result['total_time_raw'], 0))

        if first_rank_split_result['position']:
            pass_info.first_rank.position = int(first_rank_split_result['position'])

            if first_rank_split_result['laps'] < 1:
                pass_info.first_rank.last_lap_time = int(round(first_rank_split_result['total_time_raw'], 0))
            else:
                pass_info.first_rank.last_lap_time = int(round(first_rank_split_result['last_lap_raw'], 0))

    return racecontext.filters.run_filters(Flt.GAP_INFO, pass_info)

def check_win_condition_result(racecontext, **kwargs):
    raceObj = racecontext.race
    rhDataObj = racecontext.rhdata
    interfaceObj = racecontext.interface
    race_format = raceObj.format
    if race_format:
        consecutivesCount = rhDataObj.get_optionInt('consecutivesCount', 3)
        if race_format.team_racing_mode == RacingMode.TEAM_ENABLED:
            if race_format.win_condition == WinCondition.MOST_PROGRESS:
                return check_win_team_laps_and_time(racecontext, **kwargs)
            elif race_format.win_condition == WinCondition.MOST_LAPS:
                return check_win_team_most_laps(racecontext, **kwargs)
            elif race_format.win_condition == WinCondition.FIRST_TO_LAP_X:
                return check_win_team_first_to_x(racecontext, **kwargs)
            elif race_format.win_condition == WinCondition.FASTEST_LAP:
                return check_win_team_fastest_lap(racecontext, **kwargs)
            elif race_format.win_condition == WinCondition.FASTEST_CONSECUTIVE:
                return check_win_team_fastest_consecutive(racecontext, consecutivesCount, **kwargs)
            elif race_format.win_condition == WinCondition.MOST_LAPS_OVERTIME:
                return check_win_team_laps_and_overtime(racecontext, **kwargs)
        elif race_format.team_racing_mode == RacingMode.COOP_ENABLED:
            if race_format.win_condition == WinCondition.FIRST_TO_LAP_X:
                return check_win_coop_first_to_x(racecontext, **kwargs)
            else:
                return check_win_coop_most_laps(racecontext, **kwargs)
        else:
            if race_format.win_condition == WinCondition.MOST_PROGRESS:
                return check_win_laps_and_time(raceObj, interfaceObj, **kwargs)
            elif race_format.win_condition == WinCondition.MOST_LAPS:
                return check_win_most_laps(raceObj, interfaceObj, **kwargs)
            elif race_format.win_condition == WinCondition.FIRST_TO_LAP_X:
                return check_win_first_to_x(raceObj, interfaceObj, **kwargs)
            elif race_format.win_condition == WinCondition.FASTEST_LAP:
                return check_win_fastest_lap(raceObj, **kwargs)
            elif race_format.win_condition == WinCondition.FASTEST_CONSECUTIVE:
                return check_win_fastest_consecutive(raceObj, consecutivesCount, **kwargs)
            elif race_format.win_condition == WinCondition.MOST_LAPS_OVERTIME:
                return check_win_laps_and_overtime(raceObj, interfaceObj, **kwargs)
    return None

def check_win_laps_and_time(raceObj, interfaceObj, **kwargs):
    # if racing is stopped, all pilots have completed last lap after time expired,
    # or a forced determination condition, make a final call
    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs:
        leaderboard = raceObj.results['by_race_time']
        if len(leaderboard) > 1:
            lead_lap = leaderboard[0]['laps']

            if lead_lap > 0: # must have at least one lap
                # if race stopped then don't wait for crossing to finish
                if raceObj.race_status != RaceStatus.DONE:
                    # prevent win declaration if there are active crossings coming onto lead lap
                    for line in leaderboard[1:]:
                        if line['laps'] >= lead_lap - 1:
                            node = interfaceObj.nodes[line['node']]
                            if node.pass_crossing_flag:
                                logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                                return {
                                    'status': WinStatus.PENDING_CROSSING
                                }
                        else:
                            # lower results no longer need checked
                            break

                # check for tie
                if leaderboard[1]['laps'] == lead_lap:
                    if leaderboard[1]['total_time_raw'] == leaderboard[0]['total_time_raw']:
                        logger.info('Race tied at {0}/{1}'.format(leaderboard[0]['laps'], leaderboard[0]['total_time']))
                        return {
                            'status': WinStatus.TIE
                        }

                # no tie or active crossings; declare winner
                return {
                    'status': WinStatus.DECLARED,
                    'data': leaderboard[0]
                }
    elif raceObj.race_status == RaceStatus.RACING and raceObj.timer_running == False:
        # time has ended; check if winning is assured
        leaderboard = raceObj.results['by_race_time']
        if len(leaderboard) > 1:
            lead_lap = leaderboard[0]['laps']

            if lead_lap > 0: # must have at least one lap
                # prevent win declaration if there are active crossings coming onto lead lap
                for line in leaderboard[1:]:
                    if line['laps'] >= lead_lap - 1:
                        node = interfaceObj.nodes[line['node']]
                        if node.pass_crossing_flag:
                            logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                            return {
                                'status': WinStatus.PENDING_CROSSING
                            }
                    else:
                        # lower results no longer need checked
                        break

                # check if any pilot below lead can potentially pass or tie
                pilots_can_pass = 0
                for line in leaderboard[1:]:
                    if line['laps'] >= lead_lap:
                        # pilot is on lead lap
                        node_index = line['node']

                        if raceObj.get_node_finished_flag(node_index) == False:
                            pilots_can_pass += 1
                    else:
                        # lower results no longer need checked
                        break

                if pilots_can_pass == 0:
                    return check_win_laps_and_time(raceObj, interfaceObj, forced=True, **kwargs)

    return {
        'status': WinStatus.NONE
    }

def check_win_most_laps(raceObj, interfaceObj, **kwargs):
    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        leaderboard = raceObj.results['by_race_time']
        if len(leaderboard) > 1:
            lead_lap = leaderboard[0]['laps']

            if lead_lap > 0: # must have at least one lap
                # if race stopped then don't wait for crossing to finish
                if raceObj.race_status != RaceStatus.DONE:
                    # check if there are active crossings coming onto lead lap
                    for line in leaderboard[1:]:
                        if line['laps'] >= lead_lap - 1:
                            node = interfaceObj.nodes[line['node']]
                            if node.pass_crossing_flag:
                                logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                                return {
                                    'status': WinStatus.PENDING_CROSSING
                                }
                        else:
                            # lower results no longer need checked
                            break

                # check for tie
                if leaderboard[1]['laps'] == lead_lap:
                    logger.info('Race tied at %d laps', leaderboard[1]['laps'])
                    return {
                        'status': WinStatus.TIE
                    }

                # no tie or active crossings; declare winner
                return {
                    'status': WinStatus.DECLARED,
                    'data': leaderboard[0]
                }
    elif raceObj.race_status == RaceStatus.RACING and raceObj.timer_running == False:
        # time has ended; check if winning is assured
        leaderboard = raceObj.results['by_race_time']
        if len(leaderboard) > 1:
            lead_lap = leaderboard[0]['laps']

            if lead_lap > 0: # must have at least one lap
                # check if there are active crossings coming onto lead lap
                for line in leaderboard[1:]:
                    if line['laps'] >= lead_lap - 1:
                        node = interfaceObj.nodes[line['node']]
                        if node.pass_crossing_flag:
                            logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                            return {
                                'status': WinStatus.PENDING_CROSSING
                            }
                    else:
                        # lower results no longer need checked
                        break

                # check if any pilot below lead can potentially pass or tie
                pilots_can_pass = 0
                pilots_can_tie = 0
                pilots_tied = 0
                for line in leaderboard[1:]:
                    node_index = line['node']
                    if line['laps'] >= lead_lap: # pilot is on lead lap
                        pilots_tied += 1
                        if raceObj.get_node_finished_flag(node_index) == False:
                            pilots_can_pass += 1
                    elif line['laps'] >= lead_lap - 1: # pilot can reach lead lap
                        if raceObj.get_node_finished_flag(node_index) == False:
                            pilots_can_tie += 1
                    else:
                        # lower results no longer need checked
                        break

                # call race if possible
                if pilots_can_pass == 0:
                    if pilots_can_tie == 0 and pilots_tied == 0:
                        return check_win_most_laps(raceObj, interfaceObj, forced=True, **kwargs)
                    elif pilots_tied > 0: # add "and pilots_can_tie == 0" to wait for 3+-way?
                        node_index = leaderboard[0]['node']
                        if raceObj.get_node_finished_flag(node_index) == True:
                            return check_win_most_laps(raceObj, interfaceObj, forced=True, **kwargs)

    return {
        'status': WinStatus.NONE
    }

def check_win_laps_and_overtime(raceObj, interfaceObj, **kwargs):
    if (raceObj.race_status == RaceStatus.RACING and raceObj.timer_running == False) or \
                    raceObj.race_status == RaceStatus.DONE or 'at_finish' in kwargs:
        race_format = raceObj.format
        leaderboard = raceObj.results['by_race_time']

        if len(leaderboard):
            pilot_crossed_after_time = False
            for line in leaderboard:
                if line['total_time_raw'] > (race_format.race_time_sec * 1000):
                    pilot_crossed_after_time = True
                    break

            if pilot_crossed_after_time:
                return check_win_laps_and_time(raceObj, interfaceObj, **kwargs)
            else:
                win_status = check_win_most_laps(raceObj, interfaceObj, forced=True, **kwargs)
                if win_status['status'] == WinStatus.TIE and raceObj.race_status == RaceStatus.RACING:
                    # ties here change status to overtime
                    win_status['status'] = WinStatus.OVERTIME

                return win_status

    return {
        'status': WinStatus.NONE
    }

def check_win_first_to_x(raceObj, interfaceObj, **_kwargs):
    race_format = raceObj.format
    if race_format.number_laps_win: # must have laps > 0 to win
        leaderboard = raceObj.results['by_race_time']
        if len(leaderboard) > 1:
            lead_lap = leaderboard[0]['laps']

            if lead_lap >= race_format.number_laps_win: # lead lap passes win threshold
                # if race stopped then don't wait for crossing to finish
                if raceObj.race_status != RaceStatus.DONE:
                    # prevent win declaration if there are active crossings coming onto lead lap
                    for line in leaderboard[1:]: # check lower position
                        if line['laps'] >= lead_lap - 1:
                            node = interfaceObj.nodes[line['node']]
                            if node.pass_crossing_flag:
                                logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                                return {
                                    'status': WinStatus.PENDING_CROSSING
                                }
                        else:
                            # lower results no longer need checked
                            break

                # check for tie
                if leaderboard[1]['laps'] == lead_lap:
                    if leaderboard[1]['total_time_raw'] == leaderboard[0]['total_time_raw']:
                        logger.info('Race tied at {0}/{1}'.format(leaderboard[0]['laps'], leaderboard[0]['total_time']))
                        return {
                            'status': WinStatus.TIE
                        }

                # no active crossings; declare winner
                return {
                    'status': WinStatus.DECLARED,
                    'data': leaderboard[0]
                }
    return {
        'status': WinStatus.NONE
    }

def check_win_fastest_lap(raceObj, **kwargs):
    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        leaderboard = raceObj.results['by_fastest_lap']
        if len(leaderboard) > 1:
            fast_lap = leaderboard[0]['fastest_lap_raw']

            if fast_lap > 0: # must have at least one lap
                # check for tie
                if leaderboard[1]['fastest_lap_raw'] == fast_lap:
                    logger.info('Race tied at %s', leaderboard[1]['fastest_lap'])
                    return {
                        'status': WinStatus.TIE
                    }
                # declare winner
                return {
                    'status': WinStatus.DECLARED,
                    'data': leaderboard[0]
                }
    elif 'at_finish' in kwargs:
        race_format = raceObj.format
        leaderboard = raceObj.results['by_fastest_lap']
        if len(leaderboard) > 1:
            fast_lap = leaderboard[0]['fastest_lap_raw']

            if fast_lap > 0: # must have at least one lap
                max_ttc = 0

                for node in raceObj.node_laps:
                    if len(raceObj.node_laps[node]) > 0:
                        most_recent_lap = raceObj.node_laps[node][-1].lap_time_stamp
                        time_to_complete = fast_lap - ((race_format.race_time_sec * 1000) - most_recent_lap)
                        max_ttc = max(max_ttc, time_to_complete)

                max_consideration = min(fast_lap, max_ttc)
                return {
                    'status': WinStatus.NONE,
                    'max_consideration': max_consideration
                }

    return {
        'status': WinStatus.NONE
    }

def check_win_fastest_consecutive(raceObj, consecutivesCount, **kwargs):
    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        leaderboard = raceObj.results['by_consecutives']
        if len(leaderboard) > 1:
            fast_lap = leaderboard[0]['consecutives_raw']

            if fast_lap and fast_lap > consecutivesCount: # must have at least [consecutivesCount] laps
                # check for tie
                if leaderboard[1]['consecutives_raw'] == fast_lap:
                    logger.info('Race tied at %s', leaderboard[1]['consecutives'])
                    return {
                        'status': WinStatus.TIE
                    }
                # declare winner
                return {
                    'status': WinStatus.DECLARED,
                    'data': leaderboard[0]
                }
    elif 'at_finish' in kwargs:
        leaderboard = raceObj.results['by_consecutives']
        if len(leaderboard) > 1:
            fast_consecutives = leaderboard[0]['consecutives_raw']

            if fast_consecutives and fast_consecutives > 0: # must have recorded time (otherwise impossible to set bounds)
                max_node_consideration = 0
                for node in raceObj.node_laps:
                    laps = raceObj.node_laps[node]
                    if len(laps) >= (consecutivesCount - 1):
                        last_laps = sum([data.lap_time for data in laps[-consecutivesCount:]])
                        max_node_consideration = max(max_node_consideration, (fast_consecutives - last_laps))

                return {
                    'status': WinStatus.NONE,
                    'max_consideration': max_node_consideration
                }

    return {
        'status': WinStatus.NONE
    }

def check_win_team_laps_and_time(racecontext, **kwargs):
    raceObj = racecontext.race
    rhDataObj = racecontext.rhdata
    interfaceObj = racecontext.interface

    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        team_info = calc_team_leaderboard(racecontext)
        team_leaderboard = team_info['by_race_time']
        individual_leaderboard = raceObj.results['by_race_time']
        if len(team_leaderboard) > 1 and len(individual_leaderboard):
            lead_laps = team_leaderboard[0]['laps']
            lead_lap_time = team_leaderboard[0]['total_time_raw']

            if lead_laps > 0: # must have at least one lap
                # if race stopped then don't wait for crossing to finish
                if raceObj.race_status != RaceStatus.DONE:
                    # prevent win declaration if there are active crossings
                    for line in individual_leaderboard:
                        if team_info['meta']['teams'][line['team_name']]['laps'] >= lead_laps - 1: # check for deterministic crossing
                            node = interfaceObj.nodes[line['node']]
                            if node.pass_crossing_flag:
                                logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                                return {
                                    'status': WinStatus.PENDING_CROSSING
                                }

                # check for tie
                if team_leaderboard[1]['laps'] == lead_laps:
                    if team_leaderboard[1]['total_time_raw'] == team_leaderboard[0]['total_time_raw']:
                        logger.info('Race tied at {0}/{1}'.format(team_leaderboard[0]['laps'], team_leaderboard[0]['total_time']))
                        return {
                            'status': WinStatus.TIE
                        }

                # no tie or active crossings; declare winner
                return {
                    'status': WinStatus.DECLARED,
                    'data': team_leaderboard[0]
                }
    elif raceObj.race_status == RaceStatus.RACING and raceObj.timer_running == False:
        # time has ended; check if winning is assured
        team_info = calc_team_leaderboard(racecontext)
        team_leaderboard = team_info['by_race_time']
        individual_leaderboard = raceObj.results['by_race_time']
        if len(team_leaderboard) > 1 and len(individual_leaderboard):
            lead_laps = team_leaderboard[0]['laps']
            lead_lap_time = team_leaderboard[0]['total_time_raw']

            if lead_laps > 0: # must have at least one lap
                # prevent win declaration if there are active crossings
                for line in individual_leaderboard:
                    if team_info['meta']['teams'][line['team_name']]['laps'] >= lead_laps - 1: # check for deterministic crossing
                        node = interfaceObj.nodes[line['node']]
                        if node.pass_crossing_flag:
                            logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                            return {
                                'status': WinStatus.PENDING_CROSSING
                            }

                # check if team can potentially pass or tie
                teams_can_pass = 0

                team_members_finished = {}
                for line in individual_leaderboard:
                    node_index = line['node']
                    team = line['team_name']
                    if team not in team_members_finished:
                        team_members_finished[team] = 0

                    if raceObj.get_node_finished_flag(node_index):
                        team_members_finished[team] += 1

                leader_has_finished = team_members_finished[team_leaderboard[0]['name']] == team_leaderboard[0]['members']
                max_consideration = 0

                if 'overtime' in kwargs:
                    if team_members_finished[team_leaderboard[0]['name']]:
                        return check_win_team_laps_and_time(racecontext, forced=True, **kwargs)

                for line in team_leaderboard[1:]:
                    max_potential_laps = line['laps'] + line['members'] - team_members_finished[line['name']]
                    if lead_laps <= max_potential_laps:
                        teams_can_pass += 1
                    elif leader_has_finished:
                        time_to_complete = (lead_lap_time - line['total_time_raw']) * (line['members'] - team_members_finished[line['name']])
                        max_consideration = max(max_consideration, time_to_complete)

                if teams_can_pass == 0:
                    return check_win_team_laps_and_time(racecontext, forced=True, **kwargs)
                elif leader_has_finished:
                    return {
                        'status': WinStatus.NONE,
                        'max_consideration': max_consideration
                    }

    return {
        'status': WinStatus.NONE
    }

def check_win_team_most_laps(racecontext, **kwargs):
    raceObj = racecontext.race
    rhDataObj = racecontext.rhdata
    interfaceObj = racecontext.interface

    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        team_info = calc_team_leaderboard(racecontext)
        team_leaderboard = team_info['by_race_time']
        individual_leaderboard = raceObj.results['by_race_time']
        if len(team_leaderboard) > 1 and len(individual_leaderboard):
            lead_laps = team_leaderboard[0]['laps']

            if lead_laps > 0: # must have at least one lap
                # if race stopped then don't wait for crossing to finish
                if raceObj.race_status != RaceStatus.DONE:
                    # prevent win declaration if there are active crossings
                    for line in individual_leaderboard:
                        if team_info['meta']['teams'][line['team_name']]['laps'] >= lead_laps - 1: # check for deterministic crossing
                            node = interfaceObj.nodes[line['node']]
                            if node.pass_crossing_flag:
                                logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                                return {
                                    'status': WinStatus.PENDING_CROSSING
                                }

                # check for tie
                if team_leaderboard[1]['laps'] == lead_laps:
                    logger.info('Race tied at %d laps', team_leaderboard[1]['laps'])
                    return {
                        'status': WinStatus.TIE
                    }

                # no tie or active crossings; declare winner
                return {
                    'status': WinStatus.DECLARED,
                    'data': team_leaderboard[0]
                }
    elif raceObj.race_status == RaceStatus.RACING and raceObj.timer_running == False:
        # time has ended; check if winning is assured
        team_info = calc_team_leaderboard(racecontext)
        team_leaderboard = team_info['by_race_time']
        individual_leaderboard = raceObj.results['by_race_time']
        if len(team_leaderboard) > 1 and len(individual_leaderboard):
            lead_laps = team_leaderboard[0]['laps']

            if lead_laps > 0: # must have at least one lap
                # prevent win declaration if there are active crossings
                for line in individual_leaderboard:
                    if team_info['meta']['teams'][line['team_name']]['laps'] >= lead_laps - 1: # check for deterministic crossing
                        node = interfaceObj.nodes[line['node']]
                        if node.pass_crossing_flag:
                            logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                            return {
                                'status': WinStatus.PENDING_CROSSING
                            }

                # check if team can potentially pass or tie
                team_members_finished = {}
                for line in individual_leaderboard:
                    node_index = line['node']
                    team = line['team_name']
                    if team not in team_members_finished:
                        team_members_finished[team] = 0

                    if raceObj.get_node_finished_flag(node_index):
                        team_members_finished[team] += 1

                teams_can_pass = 0
                teams_can_tie = 0
                teams_tied = 0
                for line in team_leaderboard[1:]:
                    max_potential_laps = line['laps'] + line['members'] - team_members_finished[line['name']]
                    if lead_laps == line['laps']:
                        teams_tied += 1
                    if lead_laps < max_potential_laps:
                        teams_can_pass += 1
                    elif lead_laps == max_potential_laps:
                        teams_can_tie += 1

                # call race if possible
                if teams_can_pass == 0:
                    if teams_can_tie == 0 and teams_tied == 0:
                        return check_win_team_laps_and_time(racecontext, forced=True)
                    elif teams_tied > 0: # add "and teams_can_tie == 0" to wait for 3+-way?
                        leading_team = team_leaderboard[0]
                        if team_members_finished[leading_team['name']] == leading_team['members']:
                            return check_win_team_laps_and_time(racecontext, forced=True)

    return {
        'status': WinStatus.NONE
    }

def check_win_team_laps_and_overtime(racecontext, **kwargs):
    raceObj = racecontext.race
    if (raceObj.race_status == RaceStatus.RACING and raceObj.timer_running == False) or \
                    raceObj.race_status == RaceStatus.DONE or 'at_finish' in kwargs:
        race_format = raceObj.format
        leaderboard = raceObj.results['by_race_time']

        if len(leaderboard):
            pilot_crossed_after_time = False
            for line in leaderboard:
                if line['total_time_raw'] > (race_format.race_time_sec * 1000):
                    pilot_crossed_after_time = True
                    break

            if pilot_crossed_after_time:
                return check_win_team_laps_and_time(racecontext, overtime=True, **kwargs)
            else:
                win_status = check_win_team_most_laps(racecontext, forced=True, **kwargs)
                if win_status['status'] == WinStatus.TIE and raceObj.race_status == RaceStatus.RACING:
                    # ties here change status to overtime
                    win_status['status'] = WinStatus.OVERTIME

                return win_status

    return {
        'status': WinStatus.NONE
    }

def check_win_team_first_to_x(racecontext, **_kwargs):
    raceObj = racecontext.race
    rhDataObj = racecontext.rhdata
    interfaceObj = racecontext.interface

    race_format = raceObj.format
    if race_format.number_laps_win: # must have laps > 0 to win
        team_leaderboard = calc_team_leaderboard(racecontext)['by_race_time']
        individual_leaderboard = raceObj.results['by_race_time']
        if len(team_leaderboard) > 1 and len(individual_leaderboard):
            lead_lap = team_leaderboard[0]['laps']

            if lead_lap >= race_format.number_laps_win: # lead lap passes win threshold
                # if race stopped then don't wait for crossing to finish
                if raceObj.race_status != RaceStatus.DONE:
                    # prevent win declaration if there are active crossings
                    for line in individual_leaderboard:
                        node = interfaceObj.nodes[line['node']]
                        if node.pass_crossing_flag:
                            logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                            return {
                                'status': WinStatus.PENDING_CROSSING
                            }

                # check for tie
                if team_leaderboard[1]['laps'] == lead_lap:
                    logger.info('Race tied at %d laps', team_leaderboard[1]['laps'])
                    return {
                        'status': WinStatus.TIE
                    }

                # no active crossings; declare winner
                return {
                    'status': WinStatus.DECLARED,
                    'data': team_leaderboard[0]
                }
    return {
        'status': WinStatus.NONE
    }

def check_win_team_fastest_lap(racecontext, **kwargs):
    raceObj = racecontext.race
    rhDataObj = racecontext.rhdata
    interfaceObj = racecontext.interface

    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        team_leaderboard = calc_team_leaderboard(racecontext)['by_avg_fastest_lap']
        if len(team_leaderboard) > 1:
            if team_leaderboard[0]['laps'] > 0: # must have at least one lap
                # check for tie
                if team_leaderboard[1]['contribution_amt'] == team_leaderboard[0]['contribution_amt'] and \
                    team_leaderboard[1]['average_fastest_lap_raw'] == team_leaderboard[0]['average_fastest_lap_raw'] and \
                    team_leaderboard[1]['laps'] == team_leaderboard[1]['laps']:

                    logger.info('Race tied at %s', team_leaderboard[1]['average_fastest_lap'])
                    return {
                        'status': WinStatus.TIE
                    }
                # declare winner
                return {
                    'status': WinStatus.DECLARED,
                    'data': team_leaderboard[0]
                }

    elif 'at_finish' in kwargs:
        race_format = raceObj.format
        team_leaderboard = calc_team_leaderboard(racecontext)['by_avg_fastest_lap']
        if len(team_leaderboard) > 1:
            if team_leaderboard[0]['laps'] > 0: # must have at least one lap

                fast_lap_average = team_leaderboard[0]['average_fastest_lap_raw']
                if fast_lap_average > 0: # must have recorded time (otherwise impossible to set bounds)
                    team_laps = {}
                    for line in team_leaderboard:
                        team = line['name']
                        team_laps[team] = {
                            'spent_time': 0,
                            'members': line['members'],
                        }

                    for node in raceObj.node_laps:
                        if len(raceObj.node_laps[node]) > 0:
                            team = raceObj.node_teams[node]
                            if team is not None:
                                most_recent_lap = raceObj.node_laps[node][-1].lap_time_stamp
                                spent_time = ((race_format.race_time_sec * 1000) - most_recent_lap)
                                team_laps[team]['spent_time'] += spent_time

                    max_consideration = 0
                    for team in team_laps:
                        time_to_complete = fast_lap_average * team_laps[team]['members']
                        time_to_complete -= team_laps[team]['spent_time']
                        max_consideration = max(max_consideration, time_to_complete)

                        return {
                            'status': WinStatus.NONE,
                            'max_consideration': max_consideration
                        }

    return {
        'status': WinStatus.NONE
    }

def check_win_team_fastest_consecutive(racecontext, consecutivesCount, **kwargs):
    raceObj = racecontext.race
    rhDataObj = racecontext.rhdata

    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        team_leaderboard = calc_team_leaderboard(racecontext)['by_avg_consecutives']
        if len(team_leaderboard) > 1:
            race_format = raceObj.format
            if team_leaderboard[0]['laps'] > consecutivesCount or \
                (race_format.start_behavior == StartBehavior.FIRST_LAP and team_leaderboard[0]['laps'] > (consecutivesCount - 1)): # must have at least 3 laps
                # check for tie
                if team_leaderboard[1]['contribution_amt'] == team_leaderboard[0]['contribution_amt'] and \
                    team_leaderboard[1]['average_consecutives_raw'] == team_leaderboard[0]['average_consecutives_raw'] and \
                    team_leaderboard[1]['laps'] == team_leaderboard[1]['laps']:

                    logger.info('Race tied at %s', team_leaderboard[1]['average_consecutives'])
                    return {
                        'status': WinStatus.TIE
                    }
                # declare winner
                return {
                    'status': WinStatus.DECLARED,
                    'data': team_leaderboard[0]
                }
    elif 'at_finish' in kwargs:
        team_leaderboard = calc_team_leaderboard(racecontext)['by_avg_consecutives']
        if len(team_leaderboard) > 1:
            fast_consecutives = team_leaderboard[0]['average_consecutives_raw']
            if fast_consecutives and fast_consecutives > 0: # must have recorded time (otherwise impossible to set bounds)
                team_laps = {}
                for line in team_leaderboard:
                    team = line['name']
                    team_laps[team] = {
                        'time': 0,
                        'members': line['members']
                    }

                for node in raceObj.node_laps:
                    team = raceObj.node_teams[node]
                    if team is not None:
                        laps = raceObj.node_laps[node]
                        if len(laps) >= 2:
                            last_laps = sum([data.lap_time for data in laps[-consecutivesCount:]])
                            team_laps[team]['time'] += last_laps

                max_consideration = 0
                for team in team_laps:
                    if team != team_leaderboard[0]['name']: # skip leader
                        team_laps[team]['time'] = team_laps[team]['time'] / team_laps[team]['members']
                        max_consideration = max(max_consideration, fast_consecutives - team_laps[team]['time'] / team_laps[team]['members'])

                return {
                    'status': WinStatus.NONE,
                    'max_consideration': max_consideration
                }

    return {
        'status': WinStatus.NONE
    }

def check_win_coop_first_to_x(racecontext, **kwargs):
    raceObj = racecontext.race
    if raceObj.format.number_laps_win:  # must have laps > 0 to win
        leaderboard_output = calc_coop_leaderboard(racecontext)
        coop_leaderboard = leaderboard_output.get('by_race_time') if leaderboard_output else None
        if coop_leaderboard and len(coop_leaderboard) > 0:
            coop_laps = coop_leaderboard[0].get('laps')
            if type(coop_laps) is int and coop_laps >= raceObj.format.number_laps_win:  # lap passes win threshold
                return {
                    'status': WinStatus.DECLARED,
                    'data': coop_leaderboard[0],
                    'race_win_event_flag': False  # don't trigger RACE_WIN event on co-op race
                }
    return {
        'status': WinStatus.NONE
    }

def check_win_coop_most_laps(racecontext, **kwargs):
    raceObj = racecontext.race
    if (raceObj.race_status == RaceStatus.RACING and raceObj.timer_running == False) or \
                        raceObj.race_status == RaceStatus.DONE or 'at_finish' in kwargs:
        leaderboard_output = calc_coop_leaderboard(racecontext)
        coop_leaderboard = leaderboard_output.get('by_race_time') if leaderboard_output else None
        if coop_leaderboard and len(coop_leaderboard) > 0:
            coop_laps = coop_leaderboard[0].get('laps')
            if type(coop_laps) is int and coop_laps > 0:  # at least one co-op lap results in "winner" condition
                return {
                    'status': WinStatus.DECLARED,
                    'data': coop_leaderboard[0],
                    'race_win_event_flag': False  # don't trigger RACE_WIN event on co-op race
                }
    return {
        'status': WinStatus.NONE
    }

def get_leading_pilot_id(raceObj, interfaceObj, onlyNewFlag=False):
    try:
        lboard_name = raceObj.results['meta']['primary_leaderboard']
        leaderboard = raceObj.results[lboard_name]
        if len(leaderboard) > 1:  # only return leader if more than one pilot
            # check if another racer with enough laps is currently crossing
            lead_lap = leaderboard[0]['laps']
            if lead_lap > 0: # must have at least one lap
                # if race stopped then don't wait for crossing to finish
                if raceObj.race_status != RaceStatus.DONE:
                    # check if there are active crossings coming onto lead lap
                    for line in leaderboard[1:]:
                        if line['laps'] >= lead_lap - 1:
                            node = interfaceObj.nodes[line['node']]
                            if node.pass_crossing_flag:
                                logger.info('Waiting for node {0} crossing to determine leader'.format(line['node']+1))
                                return RHUtils.PILOT_ID_NONE
                pilot_id = leaderboard[0]['pilot_id']
                if onlyNewFlag:
                    if lead_lap == raceObj.race_leader_lap and pilot_id == raceObj.race_leader_pilot_id:
                        return RHUtils.PILOT_ID_NONE  # reported leader previously so return none
                prev_lead_lap = raceObj.race_leader_lap
                raceObj.race_leader_lap = lead_lap
                raceObj.race_leader_pilot_id = pilot_id
                logger.debug('Race leader pilot_id={}, lap={}, prevLap={}'.format(pilot_id, lead_lap, prev_lead_lap))
                # return ID of leader, but not if from previous lap (because of deleted lap)
                return pilot_id if lead_lap >= prev_lead_lap else RHUtils.PILOT_ID_NONE
    except Exception:
        logger.exception("Error in Results 'get_leading_pilot_id()'")
    return RHUtils.PILOT_ID_NONE

def get_leading_team_name(results):
    try:
        primary_leaderboard = results['meta']['primary_leaderboard']
        results_list = results[primary_leaderboard]
        # only return leader if more than one team and team has most laps
        if len(results_list) > 1 and results_list[0].get('laps', 0) > results_list[1].get('laps', 0):
            return results_list[0].get('name', '')
    except Exception:
        logger.exception("Error in Results 'get_leading_team_name()'")
    return ''

def get_pilot_lap_counts_str(results):
    try:
        primary_leaderboard = results['meta']['primary_leaderboard']
        results_list = results[primary_leaderboard]
        lap_strs_list = []
        for res_obj in results_list:
            lap_strs_list.append("{}={}".format(res_obj['callsign'], res_obj['laps']))
        return ", ".join(lap_strs_list)
    except Exception:
        logger.exception("Error in Results 'get_pilot_lap_totals_str()'")
    return ''

def get_team_lap_totals_str(results):
    try:
        primary_leaderboard = results['meta']['primary_leaderboard']
        results_list = results[primary_leaderboard]
        lap_strs_list = []
        for res_obj in results_list:
            lap_strs_list.append("{}={}".format(res_obj['name'], res_obj['laps']))
        lap_strs_list.sort()
        return ", ".join(lap_strs_list)
    except Exception:
        logger.exception("Error in Results 'get_team_lap_totals_str()'")
    return ''

def do_gevent_sleep(num_secs=0.001):
    # if all the calls are 'gevent.sleep(0)' then other threads get choked off,
    #  so some of the calls need to be with a parameter > 0
    gevent.sleep(num_secs)
