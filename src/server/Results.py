#
# Results generators and caching
#

import copy
import json
import gevent
import RHUtils
from RHUtils import catchLogExceptionsWrapper
import logging
from monotonic import monotonic
from eventmanager import Evt, EventManager
from RHRace import RaceStatus, StartBehavior, WinCondition, WinStatus

CACHE_TIMEOUT = 10

Events = EventManager()

logger = logging.getLogger(__name__)

class CacheStatus:
    INVALID = 'invalid'
    VALID = 'valid'

class Results():
    def __init__ (self, rhDataObj):
        self._RHData = rhDataObj

def invalidate_all_caches(rhDataObj):
    ''' Check all caches and invalidate any paused builds '''
    rhDataObj.clear_results_savedRaceMetas()
    rhDataObj.clear_results_heats()
    rhDataObj.clear_results_raceClasses()
    rhDataObj.clear_results_event()

    Events.trigger(Evt.CACHE_CLEAR)

    logger.debug('All Result caches invalidated')

def normalize_cache_status(rhDataObj):
    ''' Check all caches and invalidate any paused builds '''
    for race in rhDataObj.get_savedRaceMetas():
        if race.cacheStatus != CacheStatus.VALID:
            rhDataObj.clear_results_savedRaceMeta(race.id)

    for heat in rhDataObj.get_heats():
        if heat.cacheStatus != CacheStatus.VALID:
            rhDataObj.clear_results_heat(heat.id)

    for race_class in rhDataObj.get_raceClasses():
        if race_class.cacheStatus != CacheStatus.VALID:
            rhDataObj.clear_results_raceClass(race_class.id)

    if rhDataObj.get_results_event()['cacheStatus'] != CacheStatus.VALID:
        rhDataObj.clear_results_event()

    logger.debug('All Result caches normalized')

def build_atomic_result_cache(rhDataObj, **params):
    return {
        'results': calc_leaderboard(rhDataObj, **params),
        'cacheStatus': CacheStatus.VALID
    }

@catchLogExceptionsWrapper
def build_atomic_results_caches(rhDataObj, params):
    token = monotonic()
    timing = {
        'start': token
    }

    if 'race_id' in params:
        race = rhDataObj.set_results_savedRaceMeta(params['race_id'], {
            'cacheStatus': token
            }) 
        if 'round_id' in params:
            round_id = params['round_id']
        else:
            round_id = race.round_id

    if 'heat_id' in params:
        heat_id = params['heat_id']
        heat = rhDataObj.set_results_heat(heat_id, {
            'cacheStatus': token
            })
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

    if USE_CLASS:
        race_class = rhDataObj.set_results_raceClass(class_id, {
            'cacheStatus': token
            })

    rhDataObj.set_results_event({
        'cacheStatus': token
        })

    # rebuild race result
    if 'race_id' in params:
        gevent.sleep()
        timing['race'] = monotonic()
        if race.cacheStatus == token:
            raceResult = build_atomic_result_cache(rhDataObj, heat_id=heat_id, round_id=round_id)
            rhDataObj.set_results_savedRaceMeta(race.id, {
                'results': raceResult['results'],
                'cacheStatus': raceResult['cacheStatus']
            })
        logger.debug('Race {0} cache built in {1}s'.format(params['race_id'], monotonic() - timing['race']))

    # rebuild heat summary
    if 'heat_id' in params:
        gevent.sleep()
        timing['heat'] = monotonic()
        if heat.cacheStatus == token:
            heatResult = build_atomic_result_cache(rhDataObj, heat_id=heat_id)
            rhDataObj.set_results_heat(heat.id, {
                'results': heatResult['results'],
                'cacheStatus': heatResult['cacheStatus']
            })
        logger.debug('Heat {0} cache built in {1}s'.format(heat_id, monotonic() - timing['heat']))

    # rebuild class summary
    if USE_CLASS:
        gevent.sleep()
        timing['class'] = monotonic()
        if race_class.cacheStatus == token:
            classResult = build_atomic_result_cache(rhDataObj, class_id=class_id)
            rhDataObj.set_results_raceClass(race_class.id, {
                'results': classResult['results'],
                'cacheStatus': classResult['cacheStatus']
            })
        logger.debug('Class {0} cache built in {1}s'.format(class_id, monotonic() - timing['class']))

    # rebuild event summary
    gevent.sleep()
    timing['event'] = monotonic()
    rhDataObj.set_results_event({
        'results': json.dumps(calc_leaderboard(rhDataObj)),
        'cacheStatus': CacheStatus.VALID
        })
    logger.debug('Event cache built in %fs', monotonic() - timing['event'])

    logger.debug('Built result caches in {0}'.format(monotonic() - timing['start']))

def get_results_heat(RHData, heat):
    if len(RHData.get_savedRaceMetas_by_heat(heat.id)):
        if heat.cacheStatus == CacheStatus.INVALID:
            logger.info('Rebuilding Heat %d cache', heat.id)
            build = build_atomic_result_cache(RHData, heat_id=heat.id) 
            RHData.set_results_heat(heat.id, build)
            return {
                'result': True,
                'data': build['results']
                }
        else:
            expires = monotonic() + CACHE_TIMEOUT
            while True:
                gevent.idle()
                if heat.cacheStatus == CacheStatus.VALID:
                    return {
                        'result': True,
                        'data': heat.results
                        }
                elif monotonic() > expires:
                    return {
                        'result': False,
                        'data': None
                        }
    else:
        return {
            'result': True,
            'data': None
            }

def get_results_race_class(RHData, race_class):
    if len(RHData.get_savedRaceMetas_by_raceClass(race_class.id)):
        if race_class.cacheStatus == CacheStatus.INVALID:
            logger.info('Rebuilding Class %d cache', race_class.id)
            build = build_atomic_result_cache(RHData, class_id=race_class.id)
            RHData.set_results_raceClass(race_class.id, build)
            return {
                'result': True,
                'data': build['results']
                }
        else:
            expires = monotonic() + CACHE_TIMEOUT
            while True:
                gevent.idle()
                if race_class.cacheStatus == CacheStatus.VALID:
                    return {
                        'result': True,
                        'data': race_class.results
                        }
                elif monotonic() > expires:
                    return {
                        'result': False,
                        'data': None
                        }
    else:
        return {
            'result': True,
            'data': None
            }

def get_results_race(RHData, heat, race):
    if race.cacheStatus == CacheStatus.INVALID:
        logger.info('Rebuilding Race (Heat %d Round %d) cache', heat.id, race.round_id)
        build = build_atomic_result_cache(RHData, heat_id=heat.id, round_id=race.round_id)
        RHData.set_results_savedRaceMeta(race.id, build)
        return {
            'result': True,
            'data': build['results']
            }
    else:
        expires = monotonic() + CACHE_TIMEOUT
        while True:
            gevent.idle()
            if race.cacheStatus == CacheStatus.VALID:
                return {
                    'result': True,
                    'data': race.results
                    }
            elif monotonic() > expires:
                return {
                    'result': False,
                    'data': None
                    }

def get_results_event(RHData):
    if RHData.get_results_event()['cacheStatus'] == CacheStatus.INVALID:
        logger.info('Rebuilding Event cache')
        results = calc_leaderboard(RHData)
        RHData.set_results_event({
            'results': json.dumps(results),
            'cacheStatus': CacheStatus.VALID
            })
        return {
            'result': True,
            'data': results
            }
    else:
        expires = monotonic() + CACHE_TIMEOUT
        while True:
            gevent.idle()
            eventCache = RHData.get_results_event()
            if eventCache['cacheStatus'] == CacheStatus.VALID:
                try:
                    results = json.loads(eventCache['results'])
                    return {
                        'result': True,
                        'data': results
                        }
                except:
                    RHData.set_results_event({
                        'results': False,
                        'cacheStatus': CacheStatus.INVALID
                        })
                    logger.error('Unable to retrieve "valid" event cache from RHData')
                    return {
                        'result': False,
                        'data': None
                        }
            elif monotonic() > expires:
                logger.warning('Cache build timed out: Event Summary')
                return {
                    'result': False,
                    'data': None
                    }

def calc_leaderboard(rhDataObj, **params):
    ''' Generates leaderboards '''
    USE_CURRENT = False
    USE_ROUND = None
    USE_HEAT = None
    USE_CLASS = None

    selected_race_laps = []
    timeFormat = rhDataObj.get_option('timeFormat')

    if ('current_race' in params):
        USE_CURRENT = True

    if ('class_id' in params):
        USE_CLASS = params['class_id']
    elif ('round_id' in params and 'heat_id' in params):
        USE_ROUND = params['round_id']
        USE_HEAT = params['heat_id']
    elif ('heat_id' in params):
        USE_ROUND = None
        USE_HEAT = params['heat_id']

    # Get profile (current), frequencies (current), race query (saved), and race format (all)
    if USE_CURRENT:
        profile = params['current_profile']
        profile_freqs = json.loads(profile.frequencies)
        raceObj = params['current_race']
        race_format = raceObj.format
    else:
        if USE_CLASS:
            selected_races = rhDataObj.get_savedRaceMetas_by_raceClass(USE_CLASS)
            if len(selected_races) >= 1:
                current_format = rhDataObj.get_raceClass(USE_CLASS).format_id
            else:
                current_format = None
        elif USE_HEAT:
            if USE_ROUND:
                selected_races = [rhDataObj.get_savedRaceMeta_by_heat_round(USE_HEAT, USE_ROUND)]
                current_format = selected_races[0].format_id
            else:
                selected_races = rhDataObj.get_savedRaceMetas_by_heat(USE_HEAT)
                if len(selected_races) >= 1:
                    heat_class = selected_races[0].class_id
                    if heat_class:
                        current_format = rhDataObj.get_raceClass(heat_class).format_id
                    else:
                        current_format = None
                else:
                    current_format = None
        else:
            selected_races = rhDataObj.get_savedRaceMetas()
            current_format = None

        selected_races_keyed = {}
        for race in selected_races:
            selected_races_keyed[race.id] = race

        selected_pilotraces = {}
        racelist = []
        for race in selected_races:
            racelist.append(race.id)
            selected_pilotraces[race.id] = rhDataObj.get_savedPilotRaces_by_savedRaceMeta(race.id)

        # Generate heat list with key
        heats_keyed = {}
        all_heats = rhDataObj.get_heats()
        for heat in all_heats:
            heats_keyed[heat.id] = heat

        if current_format:
            race_format = rhDataObj.get_raceFormat(current_format)
        else:
            race_format = None

        # filter laps
        all_laps = rhDataObj.get_active_savedRaceLaps()
        for lap in all_laps:
            if lap.race_id in racelist:
                selected_race_laps.append(lap)

    gevent.sleep()

    leaderboard = []

    for pilot in rhDataObj.get_pilots():
        gevent.sleep()
        if USE_CURRENT:
            found_pilot = False
            node_index = 0
            laps = []
            for node_index in raceObj.node_pilots:
                if raceObj.node_pilots[node_index] == pilot.id and node_index < raceObj.num_nodes and len(raceObj.get_active_laps()):
                    laps = raceObj.get_active_laps()[node_index]
                    found_pilot = True
                    break

            if laps:
                if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                    total_laps = len(laps)
                else:
                    total_laps = len(laps) - 1
            else:
                total_laps = 0

            if found_pilot and profile_freqs["f"][node_index] != RHUtils.FREQUENCY_ID_NONE:
                leaderboard.append({
                    'pilot_id': pilot.id,
                    'callsign': pilot.callsign,
                    'team_name': pilot.team,
                    'laps': total_laps,
                    'holeshots': None,
                    'starts': 1 if len(laps) > 0 else 0,
                    'node': node_index,
                    'current_laps': laps
                })
        else:
            # find hole shots
            holeshot_laps = []
            pilotnode = None
            total_laps = 0
            race_starts = 0

            for race in selected_races:
                if race_format:
                    this_race_format = race_format
                else:
                    this_race_format = rhDataObj.get_raceFormat(race.format_id)

                pilotraces = selected_pilotraces[race.id]

                if len(pilotraces):
                    pilot_crossings = []
                    for lap in selected_race_laps:
                        if lap.pilot_id == pilot.id:
                            pilot_crossings.append(lap)

                    for pilotrace in pilotraces:
                        if pilotrace.pilot_id == pilot.id:
                            pilotnode = pilotrace.node_index
                            gevent.sleep()

                            race_laps = []
                            for lap in pilot_crossings:
                                if lap.pilotrace_id == pilotrace.id:
                                    race_laps.append(lap) 

                            total_laps += len(race_laps)

                            if this_race_format and this_race_format.start_behavior == StartBehavior.FIRST_LAP:
                                if len(race_laps):
                                    race_starts += 1
                            else:
                                if len(race_laps):
                                    holeshot_lap = race_laps[0]

                                    if holeshot_lap:
                                        holeshot_laps.append(holeshot_lap.id)
                                        race_starts += 1
                                        total_laps -= 1

                    pilot_laps = []
                    if len(holeshot_laps):
                        for lap in selected_race_laps:
                            if lap.pilot_id == pilot.id and \
                                lap.id not in holeshot_laps:
                                pilot_laps.append(lap)
                    else:
                        pilot_laps = pilot_crossings

            if race_starts > 0:
                leaderboard.append({
                    'pilot_id': pilot.id,
                    'callsign': pilot.callsign,
                    'team_name': pilot.team,
                    'laps': total_laps,
                    'holeshots': holeshot_laps,
                    'starts': race_starts,
                    'node': pilotnode,
                    'pilot_crossings': pilot_crossings,
                    'pilot_laps': pilot_laps
                })

    for result_pilot in leaderboard:
        gevent.sleep()

        # Get the total race time for each pilot
        if USE_CURRENT:
            race_total = 0
            laps_total = 0
            for lap in result_pilot['current_laps']:
                race_total += lap['lap_time']
                if lap['lap_number']:
                    laps_total += lap['lap_time']

            result_pilot['total_time'] = race_total
            result_pilot['total_time_laps'] = laps_total

        else:
            result_pilot['total_time'] = 0
            for lap in result_pilot['pilot_crossings']:
                result_pilot['total_time'] += lap.lap_time

            result_pilot['total_time_laps'] = 0
            for lap in result_pilot['pilot_laps']:
                result_pilot['total_time_laps'] += lap.lap_time

        gevent.sleep()
        # Get the last lap for each pilot (current race only)
        if result_pilot['laps'] == 0:
            result_pilot['last_lap'] = None # Add zero if no laps completed
        else:
            if USE_CURRENT:
                result_pilot['last_lap'] = result_pilot['current_laps'][-1]['lap_time']
            else:
                result_pilot['last_lap'] = None

        gevent.sleep()
        # Get the average lap time for each pilot
        if result_pilot['laps'] == 0:
            result_pilot['average_lap'] = 0 # Add zero if no laps completed
        else:
            if USE_CURRENT:
                if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                    avg_lap = result_pilot['current_laps'][-1]['lap_time_stamp'] / len(result_pilot['current_laps'])
                else:
                    avg_lap = (result_pilot['current_laps'][-1]['lap_time_stamp'] - result_pilot['current_laps'][0]['lap_time_stamp']) / (len(result_pilot['current_laps']) - 1)

            else:
                avg_lap = result_pilot['total_time_laps'] / result_pilot['laps']

            result_pilot['average_lap'] = avg_lap

        gevent.sleep()
        # Get the fastest lap time for each pilot
        if result_pilot['laps'] == 0:
            result_pilot['fastest_lap'] = 0 # Add zero if no laps completed
            result_pilot['fastest_lap_source'] = None
        else:
            if USE_CURRENT:
                if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                    timed_laps = result_pilot['current_laps']
                else:
                    timed_laps = filter(lambda x : x['lap_number'], result_pilot['current_laps'])

                fast_lap = sorted(timed_laps, key=lambda val : val['lap_time'])[0]['lap_time']
                result_pilot['fastest_lap'] = fast_lap
                result_pilot['fastest_lap_source'] = None
            else:
                fast_lap = None

                for lap in result_pilot['pilot_laps']:
                    if fast_lap:
                        if lap.lap_time <= fast_lap.lap_time:
                            fast_lap = lap
                    else:
                        fast_lap = lap

                if USE_HEAT:
                    result_pilot['fastest_lap_source'] = None
                else:
                    for race in selected_races:
                        if race.id == fast_lap.race_id:
                            result_pilot['fastest_lap_source'] = {
                                'round': race.round_id,
                                'heat': race.heat_id,
                                'note': heats_keyed[race.heat_id].note
                                }
                            break

                result_pilot['fastest_lap'] = fast_lap.lap_time

        gevent.sleep()
        # find best consecutive 3 laps
        if result_pilot['laps'] < 3:
            result_pilot['consecutives'] = None
            result_pilot['consecutives_source'] = None
        else:
            all_consecutives = []

            if USE_CURRENT:
                if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                    thisrace = result_pilot['current_laps']
                else:
                    thisrace = result_pilot['current_laps'][1:]

                for i in range(len(thisrace) - 2):
                    gevent.sleep()
                    all_consecutives.append({
                        'time': thisrace[i]['lap_time'] + thisrace[i+1]['lap_time'] + thisrace[i+2]['lap_time'],
                        'race_id': None,
                    })

            else:
                # build race lap store
                race_laps = {}
                for race in selected_races:
                    race_laps[race.id] = []
                    for lap in result_pilot['pilot_laps']:
                        if lap.race_id == race.id:
                            race_laps[race.id].append(lap)

                for race in selected_races:
                    gevent.sleep()

                    if len(race_laps[race.id]) >= 3:
                        for i in range(len(race_laps[race.id]) - 2):
                            gevent.sleep()
                            all_consecutives.append({
                                'time': race_laps[race.id][i].lap_time + race_laps[race.id][i+1].lap_time + race_laps[race.id][i+2].lap_time,
                                'race_id': race.id
                            })

            # Get lowest not-none value (if any)
            if all_consecutives:
                # Sort consecutives
                all_consecutives.sort(key = lambda x: (x['time'] is None, x['time']))

                result_pilot['consecutives'] = all_consecutives[0]['time']

                if USE_CURRENT:
                    result_pilot['consecutives_source'] = None
                else:
                    source_race = selected_races_keyed[all_consecutives[0]['race_id']]
                    if source_race:
                        result_pilot['consecutives_source'] = {
                            'round': source_race.round_id,
                            'heat': source_race.heat_id,
                            'note': heats_keyed[source_race.heat_id].note
                            }
                    else:
                        result_pilot['consecutives_source'] = None

            else:
                result_pilot['consecutives'] = None
                result_pilot['consecutives_source'] = None


    gevent.sleep()

    # Combine leaderboard
    for result_pilot in leaderboard:
        # Clean up calc data
        if 'current_laps' in result_pilot:
            result_pilot.pop('current_laps')
        if 'holeshots' in result_pilot:
            result_pilot.pop('holeshots')
        if 'pilot_crossings' in result_pilot:
            result_pilot.pop('pilot_crossings')
        if 'pilot_laps' in result_pilot:
            result_pilot.pop('pilot_laps')

        # formatted output
        result_pilot['total_time_raw'] = result_pilot['total_time']
        result_pilot['total_time'] = RHUtils.time_format(result_pilot['total_time'], timeFormat)

        result_pilot['total_time_laps_raw'] = result_pilot['total_time_laps']
        result_pilot['total_time_laps'] = RHUtils.time_format(result_pilot['total_time_laps'], timeFormat)

        result_pilot['average_lap_raw'] = result_pilot['average_lap']
        result_pilot['average_lap'] = RHUtils.time_format(result_pilot['average_lap'], timeFormat)

        result_pilot['fastest_lap_raw'] = result_pilot['fastest_lap']
        result_pilot['fastest_lap'] = RHUtils.time_format(result_pilot['fastest_lap'], timeFormat)

        result_pilot['consecutives_raw'] = result_pilot['consecutives']
        result_pilot['consecutives'] = RHUtils.time_format(result_pilot['consecutives'], timeFormat)

        result_pilot['last_lap_raw'] = result_pilot['last_lap']
        result_pilot['last_lap'] = RHUtils.time_format(result_pilot['last_lap'], timeFormat)

    if race_format and race_format.start_behavior == StartBehavior.STAGGERED:
        # Sort by laps time
        leaderboard_by_race_time = copy.deepcopy(sorted(leaderboard, key = lambda x: (
            -x['laps'], # reverse lap count
            x['total_time_laps_raw'] if x['total_time_laps_raw'] and x['total_time_laps_raw'] > 0 else float('inf') # total time ascending except 0
        )))

        # determine ranking
        last_rank = '-'
        last_rank_laps = 0
        last_rank_time = 0
        for i, row in enumerate(leaderboard_by_race_time, start=1):
            pos = i
            if last_rank_laps == row['laps'] and last_rank_time == row['total_time_laps_raw']:
                pos = last_rank
            last_rank = pos
            last_rank_laps = row['laps']
            last_rank_time = row['total_time_laps_raw']

            row['position'] = pos
            row['behind'] = leaderboard_by_race_time[0]['laps'] - row['laps']
    else:
        # Sort by race time
        leaderboard_by_race_time = copy.deepcopy(sorted(leaderboard, key = lambda x: (
            -x['laps'], # reverse lap count
            x['total_time_raw'] if x['total_time_raw'] and x['total_time_raw'] > 0 else float('inf') # total time ascending except 0
        )))

        # determine ranking
        last_rank = '-'
        last_rank_laps = 0
        last_rank_time = 0
        for i, row in enumerate(leaderboard_by_race_time, start=1):
            pos = i
            if last_rank_laps == row['laps'] and last_rank_time == row['total_time_raw']:
                pos = last_rank
            last_rank = pos
            last_rank_laps = row['laps']
            last_rank_time = row['total_time_raw']

            row['position'] = pos
            row['behind'] = leaderboard_by_race_time[0]['laps'] - row['laps']

    gevent.sleep()
    # Sort by fastest laps
    leaderboard_by_fastest_lap = copy.deepcopy(sorted(leaderboard, key = lambda x: (
        x['fastest_lap_raw'] if x['fastest_lap_raw'] and x['fastest_lap_raw'] > 0 else float('inf'), # fastest lap
        x['total_time_raw'] if x['total_time_raw'] and x['total_time_raw'] > 0 else float('inf') # total time
    )))

    # determine ranking
    last_rank = '-'
    last_rank_fastest_lap = 0
    for i, row in enumerate(leaderboard_by_fastest_lap, start=1):
        pos = i
        if last_rank_fastest_lap == row['fastest_lap_raw']:
            pos = last_rank
        last_rank = pos
        last_rank_fastest_lap = row['fastest_lap_raw']

        row['position'] = pos

    gevent.sleep()
    # Sort by consecutive laps
    leaderboard_by_consecutives = copy.deepcopy(sorted(leaderboard, key = lambda x: (
        x['consecutives_raw'] if x['consecutives_raw'] and x['consecutives_raw'] > 0 else float('inf'), # fastest consecutives
        -x['laps'], # lap count
        x['total_time_raw'] if x['total_time_raw'] and x['total_time_raw'] > 0 else float('inf') # total time
    )))

    # determine ranking
    last_rank = '-'
    last_rank_laps = 0
    last_rank_time = 0
    last_rank_consecutive = 0
    for i, row in enumerate(leaderboard_by_consecutives, start=1):
        pos = i
        if last_rank_consecutive == row['consecutives_raw']:
            if row['laps'] < 3:
                if last_rank_laps == row['laps'] and last_rank_time == row['total_time_raw']:
                    pos = last_rank
            else:
                pos = last_rank
        last_rank = pos
        last_rank_laps = row['laps']
        last_rank_time = row['total_time_raw']
        last_rank_consecutive = row['consecutives_raw']

        row['position'] = pos

    leaderboard_output = {
        'by_race_time': leaderboard_by_race_time,
        'by_fastest_lap': leaderboard_by_fastest_lap,
        'by_consecutives': leaderboard_by_consecutives
    }

    if race_format:
        if race_format.win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
            primary_leaderboard = 'by_consecutives'
        elif race_format.win_condition == WinCondition.FASTEST_LAP:
            primary_leaderboard = 'by_fastest_lap'
        else:
            # WinCondition.NONE
            # WinCondition.MOST_LAPS
            # WinCondition.FIRST_TO_LAP_X
            primary_leaderboard = 'by_race_time'

        leaderboard_output['meta'] = {
            'primary_leaderboard': primary_leaderboard,
            'win_condition': race_format.win_condition,
            'team_racing_mode': race_format.team_racing_mode,
            'start_behavior': race_format.start_behavior,
        }
    else:
        leaderboard_output['meta'] = {
            'primary_leaderboard': 'by_race_time',
            'win_condition': WinCondition.NONE,
            'team_racing_mode': False,
            'start_behavior': StartBehavior.HOLESHOT,
        }

    return leaderboard_output

def calc_team_leaderboard(raceObj, rhDataObj):
    '''Calculates and returns team-racing info.'''
    # Uses current results cache / requires calc_leaderboard to have been run prior
    race_format = raceObj.format

    if raceObj.results:
        results = raceObj.results['by_race_time']

        teams = {}

        for line in results:
            contributing = 0
            if race_format and race_format.win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
                if line['laps'] >= 3:
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
                if line['consecutives_raw']:
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
                    average_lap_raw = float(teams[team]['combined_average_lap_raw']) / teams[team]['contributing']

                if teams[team]['combined_fastest_lap_raw']:
                    average_fastest_lap_raw = float(teams[team]['combined_fastest_lap_raw']) / teams[team]['contributing']

                if teams[team]['combined_consecutives_raw']:
                    average_consecutives_raw = float(teams[team]['combined_consecutives_raw']) / teams[team]['contributing']

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
                'total_time': RHUtils.time_format(teams[team]['total_time_raw'], rhDataObj.get_option('timeFormat')),
                'average_lap': RHUtils.time_format(average_lap_raw, rhDataObj.get_option('timeFormat')),
                'average_fastest_lap': RHUtils.time_format(average_fastest_lap_raw, rhDataObj.get_option('timeFormat')),
                'average_consecutives': RHUtils.time_format(average_consecutives_raw, rhDataObj.get_option('timeFormat')),
            })

        # sort race_time
        leaderboard_by_race_time = copy.deepcopy(sorted(leaderboard, key = lambda x: (
            -x['laps'],
            x['average_lap_raw'] if x['average_lap_raw'] > 0 else float('inf'),
        )))

        # determine ranking
        last_rank = '-'
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
        last_rank = '-'
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
        last_rank = '-'
        last_rank_contribution_amt = 0
        last_rank_laps = 0
        last_rank_time = 0
        last_rank_consecutive = 0
        for i, row in enumerate(leaderboard_by_consecutives, start=1):
            pos = i
            if row['contribution_amt'] == last_rank_contribution_amt:
                if last_rank_consecutive == row['average_consecutives_raw']:
                    if row['laps'] < 3:
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
            if race_format.win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
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

def calc_special_class_ranking_leaderboard(rhDataObj, race_class, rounds=None):
    class_win_condition = race_class.win_condition

    if class_win_condition >= 4:
        if rounds is None:
            rounds = class_win_condition - 3

        race_format = rhDataObj.get_raceFormat(race_class.format_id)
        heats = rhDataObj.get_heats_by_class(race_class.id)

        pilotresults = {}
        for heat in heats:
            races = rhDataObj.get_savedRaceMetas_by_heat(heat.id)

            for race in races:
                race_result = get_results_race(rhDataObj, heat, race)

                for pilotresult in race_result['data']['by_race_time']:
                    if pilotresult['pilot_id'] not in pilotresults:
                        pilotresults[pilotresult['pilot_id']] = []
                    pilotresults[pilotresult['pilot_id']].append(pilotresult)

        leaderboard = []
        for pilotresultlist in pilotresults:
            pilot_result = sorted(pilotresults[pilotresultlist], key = lambda x: (
                -x['laps'], # reverse lap count
                x['total_time_laps_raw'] if x['total_time_laps_raw'] and x['total_time_laps_raw'] > 0 else float('inf') # total time ascending except 0
            ))
            pilot_result = pilot_result[:rounds]

            new_pilot_result = {}
            new_pilot_result['pilot_id'] = pilot_result[0]['pilot_id']
            new_pilot_result['callsign'] = pilot_result[0]['callsign']
            new_pilot_result['team_name'] = pilot_result[0]['team_name']
            new_pilot_result['node'] = pilot_result[0]['node']
            new_pilot_result['laps'] = 0
            new_pilot_result['starts'] = 0
            new_pilot_result['total_time_raw'] = 0
            new_pilot_result['total_time_laps_raw'] = 0

            for race in pilot_result:
                new_pilot_result['laps'] += race['laps']
                new_pilot_result['starts'] += race['starts']
                new_pilot_result['total_time_raw'] += race['total_time_raw']
                new_pilot_result['total_time_laps_raw'] += race['total_time_laps_raw']

                # new_leaderboard['fastest_lap'] += race['fastest_lap']
                # new_leaderboard['fastest_lap_source'] += race['']
                # new_leaderboard['consecutives'] += race['consecutives']
                # new_leaderboard['consecutives_source'] += race['']

            new_pilot_result['average_lap_raw'] = new_pilot_result['total_time_laps_raw'] / new_pilot_result['laps']

            timeFormat = rhDataObj.get_option('timeFormat')
            new_pilot_result['total_time'] = RHUtils.time_format(new_pilot_result['total_time_raw'], timeFormat)
            new_pilot_result['total_time_laps'] = RHUtils.time_format(new_pilot_result['total_time_laps_raw'], timeFormat)
            new_pilot_result['average_lap'] = RHUtils.time_format(new_pilot_result['average_lap_raw'], timeFormat)

            # result_pilot['fastest_lap_raw'] = result_pilot['fastest_lap']
            # result_pilot['fastest_lap'] = RHUtils.time_format(new_pilot_result['fastest_lap'], timeFormat)
            # result_pilot['consecutives_raw'] = result_pilot['consecutives']
            # result_pilot['consecutives'] = RHUtils.time_format(new_pilot_result['consecutives'], timeFormat)

            leaderboard.append(new_pilot_result)

        if race_format and race_format.start_behavior == StartBehavior.STAGGERED:
            # Sort by laps time
            leaderboard = sorted(leaderboard, key = lambda x: (
                -x['laps'], # reverse lap count
                x['total_time_laps_raw'] if x['total_time_laps_raw'] and x['total_time_laps_raw'] > 0 else float('inf') # total time ascending except 0
            ))

            # determine ranking
            last_rank = '-'
            last_rank_laps = 0
            last_rank_time = 0
            for i, row in enumerate(leaderboard, start=1):
                pos = i
                if last_rank_laps == row['laps'] and last_rank_time == row['total_time_laps_raw']:
                    pos = last_rank
                last_rank = pos
                last_rank_laps = row['laps']
                last_rank_time = row['total_time_laps_raw']

                row['position'] = pos
        else:
            # Sort by race time
            leaderboard = sorted(leaderboard, key = lambda x: (
                -x['laps'], # reverse lap count
                x['total_time_raw'] if x['total_time_raw'] and x['total_time_raw'] > 0 else float('inf') # total time ascending except 0
            ))

            # determine ranking
            last_rank = '-'
            last_rank_laps = 0
            last_rank_time = 0
            for i, row in enumerate(leaderboard, start=1):
                pos = i
                if last_rank_laps == row['laps'] and last_rank_time == row['total_time_raw']:
                    pos = last_rank
                last_rank = pos
                last_rank_laps = row['laps']
                last_rank_time = row['total_time_raw']

                row['position'] = pos
                    
        return leaderboard
    return False

def check_win_condition_result(raceObj, rhDataObj, interfaceObj, **kwargs):
    race_format = raceObj.format
    if race_format:
        if race_format.team_racing_mode:
            if race_format.win_condition == WinCondition.MOST_PROGRESS:
                return check_win_team_laps_and_time(raceObj, rhDataObj, interfaceObj, **kwargs)
            elif race_format.win_condition == WinCondition.MOST_LAPS:
                return check_win_team_most_laps(raceObj, rhDataObj, interfaceObj, **kwargs)
            elif race_format.win_condition == WinCondition.FIRST_TO_LAP_X:
                return check_win_team_first_to_x(raceObj, rhDataObj, interfaceObj, **kwargs)
            elif race_format.win_condition == WinCondition.FASTEST_LAP:
                return check_win_team_fastest_lap(raceObj, rhDataObj, **kwargs)
            elif race_format.win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
                return check_win_team_fastest_consecutive(raceObj, rhDataObj, **kwargs)
            elif race_format.win_condition == WinCondition.MOST_LAPS_OVERTIME:
                return check_win_team_laps_and_overtime(raceObj, rhDataObj, interfaceObj, **kwargs)
        else:
            if race_format.win_condition == WinCondition.MOST_PROGRESS:
                return check_win_laps_and_time(raceObj, interfaceObj, **kwargs)
            elif race_format.win_condition == WinCondition.MOST_LAPS:
                return check_win_most_laps(raceObj, interfaceObj, **kwargs)
            elif race_format.win_condition == WinCondition.FIRST_TO_LAP_X:
                return check_win_first_to_x(raceObj, interfaceObj, **kwargs)
            elif race_format.win_condition == WinCondition.FASTEST_LAP:
                return check_win_fastest_lap(raceObj, **kwargs)
            elif race_format.win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
                return check_win_fastest_consecutive(raceObj, **kwargs)
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
                        most_recent_lap = raceObj.node_laps[node][-1]['lap_time_stamp']
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

def check_win_fastest_consecutive(raceObj, **kwargs):
    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        leaderboard = raceObj.results['by_consecutives']
        if len(leaderboard) > 1:
            fast_lap = leaderboard[0]['consecutives_raw']

            if fast_lap and fast_lap > 3: # must have at least 3 laps
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
                    if len(laps) >= 2:
                        last_2_laps = laps[-1]['lap_time'] + laps[-2]['lap_time']
                        max_node_consideration = max(max_node_consideration, (fast_consecutives - last_2_laps))

                return {
                    'status': WinStatus.NONE,
                    'max_consideration': max_node_consideration
                }

    return {
        'status': WinStatus.NONE
    }

def check_win_team_laps_and_time(raceObj, rhDataObj, interfaceObj, **kwargs):
    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        team_info = calc_team_leaderboard(raceObj, rhDataObj)
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
        team_info = calc_team_leaderboard(raceObj, rhDataObj)
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
                        return check_win_team_laps_and_time(raceObj, rhDataObj, interfaceObj, forced=True, **kwargs)

                for line in team_leaderboard[1:]:
                    max_potential_laps = line['laps'] + line['members'] - team_members_finished[line['name']]
                    if lead_laps <= max_potential_laps:
                        teams_can_pass += 1
                    elif leader_has_finished:
                        time_to_complete = (lead_lap_time - line['total_time_raw']) * (line['members'] - team_members_finished[line['name']])
                        max_consideration = max(max_consideration, time_to_complete)

                if teams_can_pass == 0:
                    return check_win_team_laps_and_time(raceObj, rhDataObj, interfaceObj, forced=True, **kwargs)
                elif leader_has_finished:
                    return {
                        'status': WinStatus.NONE,
                        'max_consideration': max_consideration
                    }

    return {
        'status': WinStatus.NONE
    }

def check_win_team_most_laps(raceObj, rhDataObj, interfaceObj, **kwargs):
    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        team_info = calc_team_leaderboard(raceObj, rhDataObj)
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
        team_info = calc_team_leaderboard(raceObj, rhDataObj)
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
                        return check_win_team_laps_and_time(raceObj, rhDataObj, interfaceObj, forced=True)
                    elif teams_tied > 0: # add "and teams_can_tie == 0" to wait for 3+-way?
                        leading_team = team_leaderboard[0]
                        if team_members_finished[leading_team['name']] == leading_team['members']:
                            return check_win_team_laps_and_time(raceObj, rhDataObj, interfaceObj, forced=True)

    return {
        'status': WinStatus.NONE
    }

def check_win_team_laps_and_overtime(raceObj, rhDataObj, interfaceObj, **kwargs):
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
                return check_win_team_laps_and_time(raceObj, rhDataObj, interfaceObj, overtime=True, **kwargs)
            else:
                win_status = check_win_team_most_laps(raceObj, rhDataObj, interfaceObj, forced=True, **kwargs)
                if win_status['status'] == WinStatus.TIE and raceObj.race_status == RaceStatus.RACING:
                    # ties here change status to overtime
                    win_status['status'] = WinStatus.OVERTIME

                return win_status

    return {
        'status': WinStatus.NONE
    }

def check_win_team_first_to_x(raceObj, rhDataObj, interfaceObj, **_kwargs):
    race_format = raceObj.format
    if race_format.number_laps_win: # must have laps > 0 to win
        team_leaderboard = calc_team_leaderboard(raceObj, rhDataObj)['by_race_time']
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

def check_win_team_fastest_lap(raceObj, rhDataObj, **kwargs):
    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        team_leaderboard = calc_team_leaderboard(raceObj, rhDataObj)['by_avg_fastest_lap']
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
        team_leaderboard = calc_team_leaderboard(raceObj, rhDataObj)['by_avg_fastest_lap']
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
                                most_recent_lap = raceObj.node_laps[node][-1]['lap_time_stamp']
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

def check_win_team_fastest_consecutive(raceObj, rhDataObj, **kwargs):
    if raceObj.race_status == RaceStatus.DONE or \
                raceObj.check_all_nodes_finished() or 'forced' in kwargs: # racing must be completed
        team_leaderboard = calc_team_leaderboard(raceObj, rhDataObj)['by_avg_consecutives']
        if len(team_leaderboard) > 1:
            race_format = raceObj.format
            if team_leaderboard[0]['laps'] > 3 or \
                (race_format.start_behavior == StartBehavior.FIRST_LAP and team_leaderboard[0]['laps'] > 2): # must have at least 3 laps
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
        team_leaderboard = calc_team_leaderboard(raceObj, rhDataObj)['by_avg_consecutives']
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
                            last_2_laps = laps[-1]['lap_time'] + laps[-2]['lap_time']
                            team_laps[team]['time'] += last_2_laps

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

def get_leading_pilot_id(results):
    try:
        primary_leaderboard = results['meta']['primary_leaderboard']
        results_list = results[primary_leaderboard]
        if len(results_list) > 1:  # only return leader if more than one pilot
            return results_list[0]['pilot_id']
    except Exception:
        logger.exception("Error in Results 'get_leading_pilot_id()'")
    return RHUtils.PILOT_ID_NONE

def get_leading_team_name(results):
    try:
        primary_leaderboard = results['meta']['primary_leaderboard']
        results_list = results[primary_leaderboard]
        if len(results_list) > 1:  # only return leader if more than one team
            return results_list[0]['name']
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
