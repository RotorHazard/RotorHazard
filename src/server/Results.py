#
# Results generators and caching
#

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
from RHRace import WinCondition

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

def build_result_cache(DB, **params):
    return {
        'results': calc_leaderboard(DB, **params),
        'cacheStatus': CacheStatus.VALID
    }

@catchLogExceptionsWrapper
def build_race_results_caches(DB, params):
    global FULL_RESULTS_CACHE
    FULL_RESULTS_CACHE = False
    token = monotonic()
    timing = {
        'start': token
    }

    race = Database.SavedRaceMeta.query.get(params['race_id'])
    heat = Database.Heat.query.get(params['heat_id'])
    if heat.class_id != Database.CLASS_ID_NONE:
        race_class = Database.RaceClass.query.get(heat.class_id)

    race.cacheStatus = token
    heat.cacheStatus = token
    if heat.class_id != Database.CLASS_ID_NONE:
        race_class.cacheStatus = token
    Options.set("eventResults_cacheStatus", token)
    DB.session.commit()

    # rebuild race result
    gevent.sleep()
    timing['race'] = monotonic()
    if race.cacheStatus == token:
        raceResult = build_result_cache(DB, heat_id=params['heat_id'], round_id=params['round_id'])
        race.results = raceResult['results']
        race.cacheStatus = raceResult['cacheStatus']
        DB.session.commit()
    logger.debug('Race cache built in %fs', monotonic() - timing['race'])

    # rebuild heat summary
    gevent.sleep()
    timing['heat'] = monotonic()
    if heat.cacheStatus == token:
        heatResult = build_result_cache(DB, heat_id=params['heat_id'])
        heat.results = heatResult['results']
        heat.cacheStatus = heatResult['cacheStatus']
        DB.session.commit()
    logger.debug('Heat cache built in %fs', monotonic() - timing['heat'])

    # rebuild class summary
    if heat.class_id != Database.CLASS_ID_NONE:
        if race_class.cacheStatus == token:
            gevent.sleep()
            timing['class'] = monotonic()
            classResult = build_result_cache(DB, class_id=heat.class_id)
            race_class.results = classResult['results']
            race_class.cacheStatus = classResult['cacheStatus']
            DB.session.commit()
        logger.debug('Class cache built in %fs', monotonic() - timing['class'])

    # rebuild event summary
    gevent.sleep()
    timing['event'] = monotonic()
    Options.set("eventResults", json.dumps(calc_leaderboard(DB)))
    Options.set("eventResults_cacheStatus", CacheStatus.VALID)
    logger.debug('Event cache built in %fs', monotonic() - timing['event'])

    logger.debug('Built result caches in {0}: Race {1}, Heat {2}, Class {3}, Event'.format(monotonic() - timing['start'], params['race_id'], params['heat_id'], heat.class_id))

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
                pilotraces = Database.SavedPilotRace.query \
                    .filter(Database.SavedPilotRace.pilot_id == pilot.id, \
                    Database.SavedPilotRace.race_id == race \
                    ).all()

                if len(pilotraces):
                    pilotnode = pilotraces[-1].node_index

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
                avg_lap = (current_laps[i][-1]['lap_time_stamp'] - current_laps[i][0]['lap_time_stamp']) / (len(current_laps[i]) - 1)

                '''
                timed_laps = filter(lambda x : x['lap_number'] > 0, current_laps[i])

                lap_total = 0
                for lap in timed_laps:
                    lap_total += lap['lap_time']

                avg_lap = lap_total / len(timed_laps)
                '''

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
    # Combine for sorting
    leaderboard = list(zip(callsigns, max_laps, total_time, average_lap, fastest_lap, team_names, consecutives, fastest_lap_source, consecutives_source, last_lap, pilot_ids, nodes, total_time_laps))

    # Reverse sort max_laps x[1], then sort on total time x[2]
    leaderboard_by_race_time = sorted(leaderboard, key = lambda x: (-x[1], x[2] if x[2] and x[2] > 0 else float('inf')))

    leaderboard_total_data = []
    last_rank = '-'
    last_rank_laps = 0
    last_rank_time = RHUtils.time_format(0)
    for i, row in enumerate(leaderboard_by_race_time, start=1):
        pos = i
        total_time = RHUtils.time_format(row[2])
        if last_rank_laps == row[1] and last_rank_time == total_time:
            pos = last_rank
        last_rank = pos
        last_rank_laps = row[1]
        last_rank_time = total_time

        leaderboard_total_data.append({
            'position': pos,
            'callsign': row[0],
            'laps': row[1],
            'behind': (leaderboard_by_race_time[0][1] - row[1]),
            'total_time': RHUtils.time_format(row[2]),
            'total_time_raw': row[2],
            'total_time_laps': RHUtils.time_format(row[12]),
            'total_time_laps_raw': row[12],
            'average_lap': RHUtils.time_format(row[3]),
            'fastest_lap': RHUtils.time_format(row[4]),
            'fastest_lap_raw': row[4],
            'team_name': row[5],
            'consecutives': RHUtils.time_format(row[6]),
            'consecutives_raw': row[6],
            'fastest_lap_source': row[7],
            'consecutives_source': row[8],
            'last_lap': RHUtils.time_format(row[9]),
            'last_lap_raw': row[9],
            'pilot_id': row[10],
            'node': row[11],
        })

    gevent.sleep()
    # Sort fastest_laps x[4]
    leaderboard_by_fastest_lap = sorted(leaderboard, key = lambda x: (x[4] if x[4] and x[4] > 0 else float('inf')))

    leaderboard_fast_lap_data = []
    last_rank = '-'
    last_rank_lap = 0
    for i, row in enumerate(leaderboard_by_fastest_lap, start=1):
        pos = i
        fast_lap = RHUtils.time_format(row[4])
        if last_rank_lap == fast_lap:
            pos = last_rank
        last_rank = pos
        last_rank_laps = fast_lap

        leaderboard_fast_lap_data.append({
            'position': pos,
            'callsign': row[0],
            'laps': row[1],
            'total_time': RHUtils.time_format(row[2]),
            'total_time_raw': row[2],
            'total_time_laps': RHUtils.time_format(row[12]),
            'total_time_laps_raw': row[12],
            'average_lap': RHUtils.time_format(row[3]),
            'fastest_lap': RHUtils.time_format(row[4]),
            'fastest_lap_raw': row[4],
            'team_name': row[5],
            'consecutives': RHUtils.time_format(row[6]),
            'consecutives_raw': row[6],
            'fastest_lap_source': row[7],
            'consecutives_source': row[8],
            'last_lap': RHUtils.time_format(row[9]),
            'last_lap_raw': row[9],
            'pilot_id': row[10],
            'node': row[11],
        })

    gevent.sleep()
    # Sort consecutives x[6]
    leaderboard_by_consecutives = sorted(leaderboard, key = lambda x: (x[6] if x[6] and x[6] > 0 else float('inf')))
    logger.debug(leaderboard)
    leaderboard_consecutives_data = []
    last_rank = '-'
    last_rank_consecutive = 0
    for i, row in enumerate(leaderboard_by_consecutives, start=1):
        pos = i
        fast_consecutive = RHUtils.time_format(row[4])
        if last_rank_consecutive == fast_consecutive:
            pos = last_rank
        last_rank = pos
        last_rank_consecutive = fast_consecutive

        leaderboard_consecutives_data.append({
            'position': i,
            'callsign': row[0],
            'laps': row[1],
            'total_time': RHUtils.time_format(row[2]),
            'total_time_raw': row[2],
            'total_time_laps': RHUtils.time_format(row[12]),
            'total_time_laps_raw': row[12],
            'average_lap': RHUtils.time_format(row[3]),
            'fastest_lap': RHUtils.time_format(row[4]),
            'fastest_lap_raw': row[4],
            'team_name': row[5],
            'consecutives': RHUtils.time_format(row[6]),
            'consecutives_raw': row[6],
            'fastest_lap_source': row[7],
            'consecutives_source': row[8],
            'last_lap': RHUtils.time_format(row[9]),
            'last_lap_raw': row[9],
            'pilot_id': row[10],
            'node': row[11],
        })

    leaderboard_output = {
        'by_race_time': leaderboard_total_data,
        'by_fastest_lap': leaderboard_fast_lap_data,
        'by_consecutives': leaderboard_consecutives_data
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
        }
    else:
        leaderboard_output['meta'] = {
            'primary_leaderboard': 'by_race_time',
            'win_condition': WinCondition.NONE,
            'team_racing_mode': False
        }

    return leaderboard_output
