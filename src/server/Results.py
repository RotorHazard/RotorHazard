#
# Results generators and caching
#

import copy
import json
import gevent
import Database
import Options
import RHUtils
from RHUtils import catchLogExceptionsWrapper
import logging
from monotonic import monotonic
from Language import __
from eventmanager import Evt, EventManager
from RHRace import RaceStatus, StartBehavior, WinCondition, WinStatus

Events = EventManager()

logger = logging.getLogger(__name__)

class CacheStatus:
    INVALID = 'invalid'
    VALID = 'valid'

def invalidate_all_caches(DB):
    ''' Check all caches and invalidate any paused builds '''
    for race in Database.SavedRaceMeta.query.all():
        race.cacheStatus = CacheStatus.INVALID

    for heat in Database.Heat.query.all():
        heat.cacheStatus = CacheStatus.INVALID

    for race_class in Database.RaceClass.query.all():
        race_class.cacheStatus = CacheStatus.INVALID

    DB.session.commit()

    Options.set("eventResults_cacheStatus", CacheStatus.INVALID)

    Events.trigger(Evt.CACHE_CLEAR)

    logger.debug('All Result caches invalidated')

def normalize_cache_status(DB):
    ''' Check all caches and invalidate any paused builds '''
    for race in Database.SavedRaceMeta.query.all():
        if race.cacheStatus != CacheStatus.VALID:
            race.cacheStatus = CacheStatus.INVALID

    for heat in Database.Heat.query.all():
        if heat.cacheStatus != CacheStatus.VALID:
            heat.cacheStatus = CacheStatus.INVALID

    for race_class in Database.RaceClass.query.all():
        if race_class.cacheStatus != CacheStatus.VALID:
            race_class.cacheStatus = CacheStatus.INVALID

    if Options.get("eventResults_cacheStatus") != CacheStatus.VALID:
        Options.set("eventResults_cacheStatus", CacheStatus.INVALID)

    DB.session.commit()

    global FULL_RESULTS_CACHE_VALID
    FULL_RESULTS_CACHE_VALID = False

    logger.debug('All Result caches normalized')

def build_atomic_result_cache(DB, **params):
    return {
        'results': calc_leaderboard(DB, **params),
        'cacheStatus': CacheStatus.VALID
    }

@catchLogExceptionsWrapper
def build_atomic_results_caches(DB, params):
    global FULL_RESULTS_CACHE
    FULL_RESULTS_CACHE = False
    token = monotonic()
    timing = {
        'start': token
    }

    if 'race_id' in params:
        race = Database.SavedRaceMeta.query.get(params['race_id'])
        if 'round_id' in params:
            round_id = params['round_id']
        else:
            round_id = race.round_id

    if 'heat_id' in params:
        heat_id = params['heat_id']
        heat = Database.Heat.query.get(heat_id)
    elif 'race_id' in params:
        heat_id = race.heat_id
        heat = Database.Heat.query.get(heat_id)

    if 'class_id' in params:
        class_id = params['class_id']
        USE_CLASS = True
    elif 'heat_id' in params and heat.class_id != Database.CLASS_ID_NONE:
        class_id = heat.class_id
        USE_CLASS = True
    else:
        USE_CLASS = False

    if 'race_id' in params:
        race.cacheStatus = token
    if 'heat_id' in params:
        heat.cacheStatus = token
    if USE_CLASS:
        race_class = Database.RaceClass.query.get(class_id)
        race_class.cacheStatus = token

    Options.set("eventResults_cacheStatus", token)
    DB.session.commit()

    # rebuild race result
    if 'race_id' in params:
        gevent.sleep()
        timing['race'] = monotonic()
        if race.cacheStatus == token:
            raceResult = build_atomic_result_cache(DB, heat_id=heat_id, round_id=round_id)
            race.results = raceResult['results']
            race.cacheStatus = raceResult['cacheStatus']
            DB.session.commit()
        logger.debug('Race {0} cache built in {1}s'.format(params['race_id'], monotonic() - timing['race']))

    # rebuild heat summary
    if 'heat_id' in params:
        gevent.sleep()
        timing['heat'] = monotonic()
        if heat.cacheStatus == token:
            heatResult = build_atomic_result_cache(DB, heat_id=heat_id)
            heat.results = heatResult['results']
            heat.cacheStatus = heatResult['cacheStatus']
            DB.session.commit()
        logger.debug('Heat {0} cache built in {1}s'.format(heat_id, monotonic() - timing['heat']))

    # rebuild class summary
    if USE_CLASS:
        gevent.sleep()
        timing['class'] = monotonic()
        if race_class.cacheStatus == token:
            classResult = build_atomic_result_cache(DB, class_id=class_id)
            race_class.results = classResult['results']
            race_class.cacheStatus = classResult['cacheStatus']
            DB.session.commit()
        logger.debug('Class {0} cache built in {1}s'.format(class_id, monotonic() - timing['class']))

    # rebuild event summary
    gevent.sleep()
    timing['event'] = monotonic()
    Options.set("eventResults", json.dumps(calc_leaderboard(DB)))
    Options.set("eventResults_cacheStatus", CacheStatus.VALID)
    logger.debug('Event cache built in %fs', monotonic() - timing['event'])

    logger.debug('Built result caches in {0}'.format(monotonic() - timing['start']))

def calc_leaderboard(DB, **params):
    ''' Generates leaderboards '''
    USE_CURRENT = False
    USE_ROUND = None
    USE_HEAT = None
    USE_CLASS = None

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
        RACE = params['current_race']
        race_format = RACE.format
    else:
        if USE_CLASS:
            race_query = Database.SavedRaceMeta.query.filter_by(class_id=USE_CLASS)
            if race_query.count() >= 1:
                current_format = Database.RaceClass.query.get(USE_CLASS).format_id
            else:
                current_format = None
        elif USE_HEAT:
            if USE_ROUND:
                race_query = Database.SavedRaceMeta.query.filter_by(heat_id=USE_HEAT, round_id=USE_ROUND)
                current_format = race_query.first().format_id
            else:
                race_query = Database.SavedRaceMeta.query.filter_by(heat_id=USE_HEAT)
                if race_query.count() >= 1:
                    heat_class = race_query.first().class_id
                    if heat_class:
                        current_format = Database.RaceClass.query.get(heat_class).format_id
                    else:
                        current_format = None
                else:
                    current_format = None
        else:
            race_query = Database.SavedRaceMeta.query
            current_format = None

        selected_races = race_query.all()
        racelist = [r.id for r in selected_races]

        if current_format:
            race_format = Database.RaceFormat.query.get(current_format)
        else:
            race_format = None

    gevent.sleep()
    # Get the pilot ids for all relevant races
    # Add pilot callsigns
    # Add pilot team names
    # Get total laps for each pilot
    # Get hole shot laps
    pilot_ids = []
    callsigns = []
    nodes = []
    team_names = []
    max_laps = []
    current_laps = []
    holeshots = []

    for pilot in Database.Pilot.query.filter(Database.Pilot.id != Database.PILOT_ID_NONE):
        gevent.sleep()
        if USE_CURRENT:
            laps = []
            for node_index in RACE.node_pilots:
                if RACE.node_pilots[node_index] == pilot.id and node_index < RACE.num_nodes:
                    laps = RACE.get_active_laps()[node_index]
                    break

            if laps:
                if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                    max_lap = len(laps)
                else:
                    max_lap = len(laps) - 1
            else:
                max_lap = 0

            current_heat = Database.HeatNode.query.filter_by(heat_id=RACE.current_heat, pilot_id=pilot.id).first()
            if current_heat and profile_freqs["f"][current_heat.node_index] != RHUtils.FREQUENCY_ID_NONE:
                pilot_ids.append(pilot.id)
                callsigns.append(pilot.callsign)
                nodes.append(current_heat.node_index)
                team_names.append(pilot.team)
                max_laps.append(max_lap)
                current_laps.append(laps)
        else:
            # find hole shots
            holeshot_laps = []
            pilotnode = None
            for race in racelist:
                this_race = Database.SavedRaceMeta.query.get(race)
                this_race_format = Database.RaceFormat.query.get(this_race.format_id)

                pilotraces = Database.SavedPilotRace.query \
                    .filter(Database.SavedPilotRace.pilot_id == pilot.id, \
                    Database.SavedPilotRace.race_id == race \
                    ).all()

                if len(pilotraces):
                    pilotnode = pilotraces[-1].node_index

                if this_race_format and this_race_format.start_behavior == StartBehavior.FIRST_LAP:
                    pass
                else:
                    for pilotrace in pilotraces:
                        gevent.sleep()
                        holeshot_lap = Database.SavedRaceLap.query \
                            .filter(Database.SavedRaceLap.pilotrace_id == pilotrace.id, \
                                Database.SavedRaceLap.deleted != 1, \
                                ).order_by(Database.SavedRaceLap.lap_time_stamp).first()

                        if holeshot_lap:
                            holeshot_laps.append(holeshot_lap.id)

            # get total laps
            stat_query = DB.session.query(DB.func.count(Database.SavedRaceLap.id)) \
                .filter(Database.SavedRaceLap.pilot_id == pilot.id, \
                    Database.SavedRaceLap.deleted != 1, \
                    Database.SavedRaceLap.race_id.in_(racelist), \
                    ~Database.SavedRaceLap.id.in_(holeshot_laps))

            max_lap = stat_query.scalar()
            if max_lap > 0:
                pilot_ids.append(pilot.id)
                callsigns.append(pilot.callsign)
                team_names.append(pilot.team)
                max_laps.append(max_lap)
                holeshots.append(holeshot_laps)
                nodes.append(pilotnode)

    total_time = []
    total_time_laps = []
    last_lap = []
    average_lap = []
    fastest_lap = []
    consecutives = []
    fastest_lap_source = []
    consecutives_source = []

    for i, pilot in enumerate(pilot_ids):
        gevent.sleep()
        # Get the total race time for each pilot
        if USE_CURRENT:
            race_total = 0
            laps_total = 0
            for lap in current_laps[i]:
                race_total += lap['lap_time']
                if lap['lap_number'] > 0:
                    laps_total += lap['lap_time']

            total_time.append(race_total)
            total_time_laps.append(laps_total)

        else:
            stat_query = DB.session.query(DB.func.sum(Database.SavedRaceLap.lap_time)) \
                .filter(Database.SavedRaceLap.pilot_id == pilot, \
                    Database.SavedRaceLap.deleted != 1, \
                    Database.SavedRaceLap.race_id.in_(racelist))

            if stat_query.scalar():
                total_time.append(stat_query.scalar())
            else:
                total_time.append(0)

            stat_query = DB.session.query(DB.func.sum(Database.SavedRaceLap.lap_time)) \
                .filter(Database.SavedRaceLap.pilot_id == pilot, \
                    Database.SavedRaceLap.deleted != 1, \
                    Database.SavedRaceLap.race_id.in_(racelist), \
                    ~Database.SavedRaceLap.id.in_(holeshots[i]))

            if stat_query.scalar():
                total_time_laps.append(stat_query.scalar())
            else:
                total_time_laps.append(0)


        gevent.sleep()
        # Get the last lap for each pilot (current race only)
        if max_laps[i] == 0:
            last_lap.append(None) # Add zero if no laps completed
        else:
            if USE_CURRENT:
                last_lap.append(current_laps[i][-1]['lap_time'])
            else:
                last_lap.append(None)

        gevent.sleep()
        # Get the average lap time for each pilot
        if max_laps[i] == 0:
            average_lap.append(0) # Add zero if no laps completed
        else:
            if USE_CURRENT:
                if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                    avg_lap = current_laps[i][-1]['lap_time_stamp'] / len(current_laps[i])
                else:
                    avg_lap = (current_laps[i][-1]['lap_time_stamp'] - current_laps[i][0]['lap_time_stamp']) / (len(current_laps[i]) - 1)

            else:
                stat_query = DB.session.query(DB.func.avg(Database.SavedRaceLap.lap_time)) \
                    .filter(Database.SavedRaceLap.pilot_id == pilot, \
                        Database.SavedRaceLap.deleted != 1, \
                        Database.SavedRaceLap.race_id.in_(racelist), \
                        ~Database.SavedRaceLap.id.in_(holeshots[i]))

                avg_lap = stat_query.scalar()

            average_lap.append(avg_lap)

        gevent.sleep()
        # Get the fastest lap time for each pilot
        if max_laps[i] == 0:
            fastest_lap.append(0) # Add zero if no laps completed
            fastest_lap_source.append(None)
        else:
            if USE_CURRENT:
                if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                    timed_laps = current_laps[i]
                else:
                    timed_laps = filter(lambda x : x['lap_number'] > 0, current_laps[i])

                fast_lap = sorted(timed_laps, key=lambda val : val['lap_time'])[0]['lap_time']
                fastest_lap_source.append(None)
            else:
                stat_query = DB.session.query(DB.func.min(Database.SavedRaceLap.lap_time).label('time'), Database.SavedRaceLap.race_id) \
                    .filter(Database.SavedRaceLap.pilot_id == pilot, \
                        Database.SavedRaceLap.deleted != 1, \
                        Database.SavedRaceLap.race_id.in_(racelist), \
                        ~Database.SavedRaceLap.id.in_(holeshots[i])).one()

                fast_lap = stat_query.time

                if USE_HEAT:
                    fastest_lap_source.append(None)
                else:
                    source_query = Database.SavedRaceMeta.query.get(stat_query.race_id)
                    fast_lap_round = source_query.round_id
                    fast_lap_heat = source_query.heat_id
                    fast_lap_heatnote = Database.Heat.query.get(fast_lap_heat).note

                    if fast_lap_heatnote:
                        source_text = fast_lap_heatnote + ' / ' + __('Round') + ' ' + str(fast_lap_round)
                    else:
                        source_text = __('Heat') + ' ' + str(fast_lap_heat) + ' / ' + __('Round') + ' ' + str(fast_lap_round)

                    fastest_lap_source.append(source_text)

            fastest_lap.append(fast_lap)

        gevent.sleep()
        # find best consecutive 3 laps
        if max_laps[i] < 3:
            consecutives.append(None)
            consecutives_source.append(None)
        else:
            all_consecutives = []

            if USE_CURRENT:
                thisrace = current_laps[i][1:]

                for j in range(len(thisrace) - 2):
                    gevent.sleep()
                    all_consecutives.append({
                        'time': thisrace[j]['lap_time'] + thisrace[j+1]['lap_time'] + thisrace[j+2]['lap_time'],
                        'race_id': None,
                    })

            else:
                for race_id in racelist:
                    gevent.sleep()
                    thisrace = DB.session.query(Database.SavedRaceLap.lap_time) \
                        .filter(Database.SavedRaceLap.pilot_id == pilot, \
                            Database.SavedRaceLap.race_id == race_id, \
                            Database.SavedRaceLap.deleted != 1, \
                            ~Database.SavedRaceLap.id.in_(holeshots[i]) \
                            ).all()

                    if len(thisrace) >= 3:
                        for j in range(len(thisrace) - 2):
                            gevent.sleep()
                            all_consecutives.append({
                                'time': thisrace[j].lap_time + thisrace[j+1].lap_time + thisrace[j+2].lap_time,
                                'race_id': race_id
                            })

            # Sort consecutives
            all_consecutives.sort(key = lambda x: (x['time'] is None, x['time']))
            # Get lowest not-none value (if any)

            if all_consecutives:
                consecutives.append(all_consecutives[0]['time'])

                if USE_CURRENT:
                    consecutives_source.append(None)
                else:
                    source_query = Database.SavedRaceMeta.query.get(all_consecutives[0]['race_id'])
                    if source_query:
                        fast_lap_round = source_query.round_id
                        fast_lap_heat = source_query.heat_id
                        fast_lap_heatnote = Database.Heat.query.get(fast_lap_heat).note

                        if fast_lap_heatnote:
                            source_text = fast_lap_heatnote + ' / ' + __('Round') + ' ' + str(fast_lap_round)
                        else:
                            source_text = __('Heat') + ' ' + str(fast_lap_heat) + ' / ' + __('Round') + ' ' + str(fast_lap_round)

                        consecutives_source.append(source_text)
                    else:
                        consecutives_source.append(None)

            else:
                consecutives.append(None)
                consecutives_source.append(None)

    gevent.sleep()

    # Combine leaderboard
    leaderboard = []
    for i, pilot in enumerate(pilot_ids):
        leaderboard.append({
            'callsign': callsigns[i],
            'laps': max_laps[i],
            'total_time': RHUtils.time_format(total_time[i]),
            'total_time_raw': total_time[i],
            'total_time_laps': RHUtils.time_format(total_time_laps[i]),
            'total_time_laps_raw': total_time_laps[i],
            'average_lap': RHUtils.time_format(average_lap[i]),
            'average_lap_raw': average_lap[i],
            'fastest_lap': RHUtils.time_format(fastest_lap[i]),
            'fastest_lap_raw': fastest_lap[i],
            'team_name': team_names[i],
            'consecutives': RHUtils.time_format(consecutives[i]),
            'consecutives_raw': consecutives[i],
            'fastest_lap_source': fastest_lap_source[i],
            'consecutives_source': consecutives_source,
            'last_lap': RHUtils.time_format(last_lap[i]),
            'last_lap_raw': last_lap[i],
            'pilot_id': pilot,
            'node': nodes[i],
        })

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

def calc_team_leaderboard(RACE):
    '''Calculates and returns team-racing info.'''
    # Uses current results cache / requires calc_leaderboard to have been run prior
    race_format = RACE.format

    if RACE.results:
        results = RACE.results['by_race_time']

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
                'total_time': RHUtils.time_format(teams[team]['total_time_raw']),
                'average_lap': RHUtils.time_format(average_lap_raw),
                'average_fastest_lap': RHUtils.time_format(average_fastest_lap_raw),
                'average_consecutives': RHUtils.time_format(average_consecutives_raw),
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

def get_lap_info(RACE, seat_index):
    ''' Assembles current lap information for OSD '''
    # Ensure race result cache is valid before calling

    # select correct results
    win_condition = RACE.format.win_condition

    if win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
        leaderboard = RACE.results['by_consecutives']
    elif win_condition == WinCondition.FASTEST_LAP:
        leaderboard = RACE.results['by_fastest_lap']
    else:
        # WinCondition.MOST_LAPS
        # WinCondition.FIRST_TO_LAP_X
        # WinCondition.NONE
        leaderboard = RACE.results['by_race_time']

    # get this seat's results
    for index, result in enumerate(leaderboard):
        if result['node'] == seat_index: #TODO issue408
            rank_index = index
            break

    # check for best lap
    is_best_lap = False
    if result['fastest_lap_raw'] == result['last_lap_raw']:
        is_best_lap = True

    # get the next faster results
    next_rank_split = None
    next_rank_split_result = None
    if result['position'] > 1:
        next_rank_split_result = leaderboard[rank_index - 1]

        if next_rank_split_result['total_time_raw']:
            if win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
                if next_rank_split_result['consecutives_raw']:
                    next_rank_split = result['consecutives_raw'] - next_rank_split_result['consecutives_raw']
            elif win_condition == WinCondition.FASTEST_LAP:
                if next_rank_split_result['fastest_lap_raw']:
                    next_rank_split = result['last_lap_raw'] - next_rank_split_result['fastest_lap_raw']
            else:
                # WinCondition.MOST_LAPS
                # WinCondition.FIRST_TO_LAP_X
                next_rank_split = result['total_time_raw'] - next_rank_split_result['total_time_raw']
                next_rank_split_fastest = ''
    else:
        # check split to self
        next_rank_split_result = leaderboard[rank_index]

        if win_condition == WinCondition.FASTEST_3_CONSECUTIVE or win_condition == WinCondition.FASTEST_LAP:
            if next_rank_split_result['fastest_lap_raw']:
                if result['last_lap_raw'] > next_rank_split_result['fastest_lap_raw']:
                    next_rank_split = result['last_lap_raw'] - next_rank_split_result['fastest_lap_raw']

    # get the fastest result
    first_rank_split = None
    first_rank_split_result = None
    if result['position'] > 2:
        first_rank_split_result = leaderboard[0]

        if next_rank_split_result['total_time_raw']:
            if win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
                if first_rank_split_result['consecutives_raw']:
                    first_rank_split = result['consecutives_raw'] - first_rank_split_result['consecutives_raw']
            elif win_condition == WinCondition.FASTEST_LAP:
                if first_rank_split_result['fastest_lap_raw']:
                    first_rank_split = result['last_lap_raw'] - first_rank_split_result['fastest_lap_raw']
            else:
                # WinCondition.MOST_LAPS
                # WinCondition.FIRST_TO_LAP_X
                first_rank_split = result['total_time_raw'] - first_rank_split_result['total_time_raw']

    '''
    Set up output objects
    '''

    lap_info = {
        'race': {},
        'current': {},
        'next_rank': {},
        'first_rank': {},
    }

    # Race
    lap_info['race'] = {
        'win_condition': win_condition
    }

    # Current pilot
    lap_info['current'] = {
        'seat': seat_index,
        'position': str(result['position']),
        'callsign': result['callsign'],
        'lap_number': '',
        'last_lap_time': '',
        'total_time': result['total_time'],
        'total_time_laps': result['total_time_laps'],
        'consecutives': result['consecutives'],
        'is_best_lap': is_best_lap,
    }

    if result['laps']:
        lap_info['current']['lap_number'] = str(result['laps'])
        lap_info['current']['last_lap_time'] = result['last_lap']
    else:
        lap_info['current']['lap_prefix'] = ''
        lap_info['current']['lap_number'] = __('HS')
        lap_info['current']['last_lap_time'] = result['total_time']
        lap_info['current']['is_best_lap'] = False

    # Next faster pilot
    lap_info['next_rank'] = {
        'seat': None,
        'position': None,
        'callsign': None,
        'split_time': None,
        'lap_number': None,
        'last_lap_time': None,
        'total_time': None,
    }

    if next_rank_split:
        lap_info['next_rank'] = {
            'seat': next_rank_split_result['node'],
            'position': str(next_rank_split_result['position']),
            'callsign': next_rank_split_result['callsign'],
            'split_time': RHUtils.time_format(next_rank_split),
            'lap_number': str(next_rank_split_result['laps']),
            'last_lap_time': next_rank_split_result['last_lap'],
            'total_time': next_rank_split_result['total_time'],
        }

        if next_rank_split_result['laps'] < 1:
            lap_info['next_rank']['lap_number'] = __('HS')
            lap_info['next_rank']['last_lap_time'] = next_rank_split_result['total_time']

    # Race Leader
    lap_info['first_rank'] = {
        'seat': None,
        'position': None,
        'callsign': None,
        'split_time': None,
        'lap_number': None,
        'last_lap_time': None,
        'total_time': None,
    }

    if first_rank_split:
        lap_info['first_rank'] = {
            'seat': first_rank_split_result['node'],
            'position': str(first_rank_split_result['position']),
            'callsign': first_rank_split_result['callsign'],
            'split_time': RHUtils.time_format(first_rank_split),
            'lap_number': str(first_rank_split_result['laps']),
            'last_lap_time': first_rank_split_result['last_lap'],
            'total_time': first_rank_split_result['total_time'],
        }

        if next_rank_split_result['laps'] < 1:
            lap_info['first_rank']['lap_number'] = __('HS')
            lap_info['first_rank']['last_lap_time'] = first_rank_split_result['total_time']

    return lap_info

def check_win_condition(RACE, INTERFACE, **kwargs):
    if RACE.win_status in [WinStatus.NONE, WinStatus.PENDING_CROSSING, WinStatus.OVERTIME]:
        race_format = RACE.format
        if race_format:
            if race_format.team_racing_mode:
                if race_format.win_condition == WinCondition.MOST_PROGRESS:
                    return check_win_team_laps_and_time(RACE, INTERFACE, **kwargs)
                elif race_format.win_condition == WinCondition.MOST_LAPS:
                    return check_win_team_most_laps(RACE, INTERFACE, **kwargs)
                elif race_format.win_condition == WinCondition.FIRST_TO_LAP_X:
                    return check_win_team_first_to_x(RACE, INTERFACE, **kwargs)
                elif race_format.win_condition == WinCondition.FASTEST_LAP:
                    return check_win_team_fastest_lap(RACE, **kwargs)
                elif race_format.win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
                    return check_win_team_fastest_consecutive(RACE, **kwargs)
                elif race_format.win_condition == WinCondition.MOST_LAPS_OVERTIME:
                    return check_win_team_laps_and_overtime(RACE, INTERFACE, **kwargs)
            else:
                if race_format.win_condition == WinCondition.MOST_PROGRESS:
                    return check_win_laps_and_time(RACE, INTERFACE, **kwargs)
                elif race_format.win_condition == WinCondition.MOST_LAPS:
                    return check_win_most_laps(RACE, INTERFACE, **kwargs)
                elif race_format.win_condition == WinCondition.FIRST_TO_LAP_X:
                    return check_win_first_to_x(RACE, INTERFACE, **kwargs)
                elif race_format.win_condition == WinCondition.FASTEST_LAP:
                    return check_win_fastest_lap(RACE, **kwargs)
                elif race_format.win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
                    return check_win_fastest_consecutive(RACE, **kwargs)
                elif race_format.win_condition == WinCondition.MOST_LAPS_OVERTIME:
                    return check_win_laps_and_overtime(RACE, INTERFACE, **kwargs)

    return None

def check_win_laps_and_time(RACE, INTERFACE, **kwargs):
    # if racing is stopped, all pilots have completed last lap after time expired,
    # or a forced determination condition, make a final call
    if RACE.race_status == RaceStatus.DONE or \
        False not in RACE.node_has_finished.values() or \
        'forced' in kwargs:
        leaderboard = RACE.results['by_race_time']
        if len(leaderboard) > 1:
            lead_lap = leaderboard[0]['laps']
            lead_lap_time = leaderboard[0]['total_time_raw']

            if lead_lap > 0: # must have at least one lap
                # prevent win declaration if there are active crossings coming onto lead lap
                for line in leaderboard[1:]:
                    if line['laps'] >= lead_lap - 1:
                        node = INTERFACE.nodes[line['node']]
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
    elif RACE.race_status == RaceStatus.RACING and RACE.timer_running == False:
        # time has ended; check if winning is assured
        leaderboard = RACE.results['by_race_time']
        if len(leaderboard) > 1:
            lead_lap = leaderboard[0]['laps']
            lead_lap_time = leaderboard[0]['total_time_raw']

            if lead_lap > 0: # must have at least one lap
                # prevent win declaration if there are active crossings coming onto lead lap
                for line in leaderboard[1:]:
                    if line['laps'] >= lead_lap - 1:
                        node = INTERFACE.nodes[line['node']]
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

                        if RACE.node_has_finished[node_index] == False:
                            pilots_can_pass += 1
                    else:
                        # lower results no longer need checked
                        break

                if pilots_can_pass == 0:
                    return check_win_laps_and_time(RACE, INTERFACE, forced=True, **kwargs)

    return {
        'status': WinStatus.NONE
    }

def check_win_most_laps(RACE, INTERFACE, **kwargs):
    if RACE.race_status == RaceStatus.DONE or \
        False not in RACE.node_has_finished.values() or \
        'forced' in kwargs: # racing must be completed
        leaderboard = RACE.results['by_race_time']
        if len(leaderboard) > 1:
            lead_lap = leaderboard[0]['laps']

            if lead_lap > 0: # must have at least one lap
                # check if there are active crossings coming onto lead lap
                for line in leaderboard[1:]:
                    if line['laps'] >= lead_lap - 1:
                        node = INTERFACE.nodes[line['node']]
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
    elif RACE.race_status == RaceStatus.RACING and RACE.timer_running == False:
        # time has ended; check if winning is assured
        leaderboard = RACE.results['by_race_time']
        if len(leaderboard) > 1:
            lead_lap = leaderboard[0]['laps']

            if lead_lap > 0: # must have at least one lap
                # check if there are active crossings coming onto lead lap
                for line in leaderboard[1:]:
                    if line['laps'] >= lead_lap - 1:
                        node = INTERFACE.nodes[line['node']]
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
                        if RACE.node_has_finished[node_index] == False:
                            pilots_can_pass += 1
                    elif line['laps'] >= lead_lap - 1: # pilot can reach lead lap
                        if RACE.node_has_finished[node_index] == False:
                            pilots_can_tie += 1
                    else:
                        # lower results no longer need checked
                        break

                # call race if possible
                if pilots_can_pass == 0:
                    if pilots_can_tie == 0 and pilots_tied == 0:
                        return check_win_most_laps(RACE, INTERFACE, forced=True, **kwargs)
                    elif pilots_tied > 0: # add "and pilots_can_tie == 0" to wait for 3+-way?
                        node_index = leaderboard[0]['node']
                        if RACE.node_has_finished[node_index] == True:
                            return check_win_most_laps(RACE, INTERFACE, forced=True, **kwargs)

    return {
        'status': WinStatus.NONE
    }

def check_win_laps_and_overtime(RACE, INTERFACE, **kwargs):
    if RACE.race_status == RaceStatus.DONE:
        # manually stopping race always most laps only
        return check_win_most_laps(RACE, INTERFACE, forced=True, **kwargs)

    elif (RACE.race_status == RaceStatus.RACING and RACE.timer_running == False) or \
        'at_finish' in kwargs:
        race_format = RACE.format
        leaderboard = RACE.results['by_race_time']
        if len(leaderboard):
            pilot_crossed_after_time = False
            for line in leaderboard:
                if line['total_time_raw'] > (race_format.race_time_sec * 1000):
                    pilot_crossed_after_time = True
                    break

            if pilot_crossed_after_time:
                return check_win_laps_and_time(RACE, INTERFACE, **kwargs)
            else:
                win_status = check_win_most_laps(RACE, INTERFACE, forced=True, **kwargs)
                if win_status['status'] == WinStatus.TIE:
                    # ties here change status to overtime
                    win_status['status'] = WinStatus.OVERTIME

                return win_status

    return {
        'status': WinStatus.NONE
    }

def check_win_first_to_x(RACE, INTERFACE, **kwargs):
    race_format = RACE.format
    if race_format.number_laps_win: # must have laps > 0 to win
        leaderboard = RACE.results['by_race_time']
        if len(leaderboard) > 1:
            lead_lap = leaderboard[0]['laps']

            if lead_lap >= race_format.number_laps_win: # lead lap passes win threshold
                # prevent win declaration if there are active crossings coming onto lead lap
                for line in leaderboard[1:]: # check lower position
                    if line['laps'] >= lead_lap - 1:
                        node = INTERFACE.nodes[line['node']]
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

def check_win_fastest_lap(RACE, **kwargs):
    if RACE.race_status == RaceStatus.DONE or \
        False not in RACE.node_has_finished.values() or \
        'forced' in kwargs: # racing must be completed
        leaderboard = RACE.results['by_fastest_lap']
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
        race_format = RACE.format
        leaderboard = RACE.results['by_fastest_lap']
        if len(leaderboard) > 1:
            fast_lap = leaderboard[0]['fastest_lap_raw']

            if fast_lap > 0: # must have at least one lap
                max_ttc = 0

                for node in RACE.node_laps:
                    if len(RACE.node_laps[node]) > 0:
                        most_recent_lap = RACE.node_laps[node][-1]['lap_time_stamp']
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

def check_win_fastest_consecutive(RACE, **kwargs):
    if RACE.race_status == RaceStatus.DONE or \
        False not in RACE.node_has_finished.values() or \
        'forced' in kwargs: # racing must be completed
        leaderboard = RACE.results['by_consecutives']
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
        leaderboard = RACE.results['by_consecutives']
        if len(leaderboard) > 1:
            fast_consecutives = leaderboard[0]['consecutives_raw']

            if fast_consecutives > 0: # must have recorded time (otherwise impossible to set bounds)
                max_node_consideration = 0
                for node in RACE.node_laps:
                    laps = RACE.node_laps[node]
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

def check_win_team_laps_and_time(RACE, INTERFACE, **kwargs):
    if RACE.race_status == RaceStatus.DONE or \
        False not in RACE.node_has_finished.values() or \
        'forced' in kwargs: # racing must be completed
        team_info = calc_team_leaderboard(RACE)
        team_leaderboard = team_info['by_race_time']
        individual_leaderboard = RACE.results['by_race_time']
        if len(team_leaderboard) > 1 and len(individual_leaderboard):
            lead_laps = team_leaderboard[0]['laps']
            lead_lap_time = team_leaderboard[0]['total_time_raw']

            if lead_laps > 0: # must have at least one lap
                # prevent win declaration if there are active crossings
                for line in individual_leaderboard:
                    if team_info['meta']['teams'][line['team_name']]['laps'] >= lead_laps - 1: # check for deterministic crossing
                        node = INTERFACE.nodes[line['node']]
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
    elif RACE.race_status == RaceStatus.RACING and RACE.timer_running == False:
        # time has ended; check if winning is assured
        team_info = calc_team_leaderboard(RACE)
        team_leaderboard = team_info['by_race_time']
        individual_leaderboard = RACE.results['by_race_time']
        if len(team_leaderboard) > 1 and len(individual_leaderboard):
            lead_laps = team_leaderboard[0]['laps']
            lead_lap_time = team_leaderboard[0]['total_time_raw']

            if lead_laps > 0: # must have at least one lap
                # prevent win declaration if there are active crossings
                for line in individual_leaderboard:
                    if team_info['meta']['teams'][line['team_name']]['laps'] >= lead_laps - 1: # check for deterministic crossing
                        node = INTERFACE.nodes[line['node']]
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

                    if RACE.node_has_finished[node_index]:
                        team_members_finished[team] += 1

                leader_has_finished = team_members_finished[team_leaderboard[0]['name']] == team_leaderboard[0]['members']
                max_consideration = 0

                if 'overtime' in kwargs:
                    if team_members_finished[team_leaderboard[0]['name']]:
                        return check_win_team_laps_and_time(RACE, INTERFACE, forced=True, **kwargs)

                for line in team_leaderboard[1:]:
                    max_potential_laps = line['laps'] + line['members'] - team_members_finished[line['name']]
                    if lead_laps <= max_potential_laps:
                        teams_can_pass += 1
                    elif leader_has_finished:
                        time_to_complete = (lead_lap_time - line['total_time_raw']) * (line['members'] - team_members_finished[line['name']])
                        max_consideration = max(max_consideration, time_to_complete)

                if teams_can_pass == 0:
                    return check_win_team_laps_and_time(RACE, INTERFACE, forced=True, **kwargs)
                elif leader_has_finished:
                    return {
                        'status': WinStatus.NONE,
                        'max_consideration': max_consideration
                    }

    return {
        'status': WinStatus.NONE
    }

def check_win_team_most_laps(RACE, INTERFACE, **kwargs):
    if RACE.race_status == RaceStatus.DONE or \
        False not in RACE.node_has_finished.values() or \
        'forced' in kwargs: # racing must be completed
        team_info = calc_team_leaderboard(RACE)
        team_leaderboard = team_info['by_race_time']
        individual_leaderboard = RACE.results['by_race_time']
        if len(team_leaderboard) > 1 and len(individual_leaderboard):
            lead_laps = team_leaderboard[0]['laps']

            if lead_laps > 0: # must have at least one lap
                # prevent win declaration if there are active crossings
                for line in individual_leaderboard:
                    if team_info['meta']['teams'][line['team_name']]['laps'] >= lead_laps - 1: # check for deterministic crossing
                        node = INTERFACE.nodes[line['node']]
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
    elif RACE.race_status == RaceStatus.RACING and RACE.timer_running == False:
        # time has ended; check if winning is assured
        team_info = calc_team_leaderboard(RACE)
        team_leaderboard = team_info['by_race_time']
        individual_leaderboard = RACE.results['by_race_time']
        if len(team_leaderboard) > 1 and len(individual_leaderboard):
            lead_laps = team_leaderboard[0]['laps']

            if lead_laps > 0: # must have at least one lap
                # prevent win declaration if there are active crossings
                for line in individual_leaderboard:
                    if team_info['meta']['teams'][line['team_name']]['laps'] >= lead_laps - 1: # check for deterministic crossing
                        node = INTERFACE.nodes[line['node']]
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

                    if RACE.node_has_finished[node_index]:
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
                        return check_win_team_laps_and_time(RACE, INTERFACE, forced=True)
                    elif teams_tied > 0: # add "and teams_can_tie == 0" to wait for 3+-way?
                        leading_team = team_leaderboard[0]
                        if team_members_finished[leading_team['name']] == leading_team['members']:
                            return check_win_team_laps_and_time(RACE, INTERFACE, forced=True)

    return {
        'status': WinStatus.NONE
    }

def check_win_team_laps_and_overtime(RACE, INTERFACE, **kwargs):
    if RACE.race_status == RaceStatus.DONE:
        # manually stopping race always most laps only
        return check_win_team_most_laps(RACE, INTERFACE, forced=True, **kwargs)

    elif (RACE.race_status == RaceStatus.RACING and RACE.timer_running == False) or \
        'at_finish' in kwargs:
        race_format = RACE.format
        leaderboard = RACE.results['by_race_time']
        if len(leaderboard):
            pilot_crossed_after_time = False
            for line in leaderboard:
                if line['total_time_raw'] > (race_format.race_time_sec * 1000):
                    pilot_crossed_after_time = True
                    break

            if pilot_crossed_after_time:
                return check_win_team_laps_and_time(RACE, INTERFACE, overtime=True, **kwargs)
            else:
                win_status = check_win_team_most_laps(RACE, INTERFACE, forced=True, **kwargs)
                if win_status['status'] == WinStatus.TIE:
                    # ties here change status to overtime
                    win_status['status'] = WinStatus.OVERTIME

                return win_status

    return {
        'status': WinStatus.NONE
    }

def check_win_team_first_to_x(RACE, INTERFACE, **kwargs):
    race_format = RACE.format
    if race_format.number_laps_win: # must have laps > 0 to win
        team_leaderboard = calc_team_leaderboard(RACE)['by_race_time']
        individual_leaderboard = RACE.results['by_race_time']
        if len(team_leaderboard) > 1 and len(individual_leaderboard):
            lead_lap = team_leaderboard[0]['laps']

            if lead_lap >= race_format.number_laps_win: # lead lap passes win threshold
                # prevent win declaration if there are active crossings
                for line in individual_leaderboard:
                    node = INTERFACE.nodes[line['node']]
                    if node.pass_crossing_flag:
                        logger.info('Waiting for node {0} crossing to decide winner'.format(line['node']+1))
                        return {
                            'status': WinStatus.PENDING_CROSSING
                        }

                # check for tie
                if team_leaderboard[1]['laps'] == lead_lap:
                    logger.info('Race tied at %d laps', team_leaderboard[1]['laps'])
                    # TODO: DECLARED_TIE ***
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

def check_win_team_fastest_lap(RACE, **kwargs):
    if RACE.race_status == RaceStatus.DONE or \
        False not in RACE.node_has_finished.values() or \
        'forced' in kwargs: # racing must be completed
        team_leaderboard = calc_team_leaderboard(RACE)['by_avg_fastest_lap']
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
        race_format = RACE.format
        team_leaderboard = calc_team_leaderboard(RACE)['by_avg_fastest_lap']
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

                    for node in RACE.node_laps:
                        if len(RACE.node_laps[node]) > 0:
                            team = RACE.node_teams[node]
                            if team is not None:
                                most_recent_lap = RACE.node_laps[node][-1]['lap_time_stamp']
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

def check_win_team_fastest_consecutive(RACE, **kwargs):
    if RACE.race_status == RaceStatus.DONE or \
        False not in RACE.node_has_finished.values() or \
        'forced' in kwargs: # racing must be completed
        team_leaderboard = calc_team_leaderboard(RACE)['by_avg_consecutives']
        if len(team_leaderboard) > 1:
            if team_leaderboard[0]['laps'] > 3: # must have at least 3 laps
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
        team_leaderboard = calc_team_leaderboard(RACE)['by_avg_consecutives']
        if len(team_leaderboard) > 1:
            fast_consecutives = team_leaderboard[0]['average_consecutives_raw']
            if fast_consecutives > 0: # must have recorded time (otherwise impossible to set bounds)
                team_laps = {}
                for line in team_leaderboard:
                    team = line['name']
                    team_laps[team] = {
                        'time': 0,
                        'members': line['members']
                    }

                for node in RACE.node_laps:
                    team = RACE.node_teams[node]
                    if team is not None:
                        laps = RACE.node_laps[node]
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

