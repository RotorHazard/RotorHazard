#
# Results generators and caching
#

import json
import gevent
import Database
import Options
import logging
from Language import __
from eventmanager import Evt, EventManager
from RHRace import WinCondition
Events = EventManager()

logger = logging.getLogger(__name__)

FREQUENCY_ID_NONE = 0  # indicator value for node disabled

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

    global FULL_RESULTS_CACHE_VALID
    FULL_RESULTS_CACHE_VALID = False

    Events.trigger(Evt.CACHE_CLEAR)

    logger.info('All Result caches invalidated')

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

    logger.info('All Result caches normalized')

def build_result_cache(results, cacheStatus, **params):
    return {
        'results': calc_leaderboard(**params),
        'cacheStatus': CacheStatus.VALID
    }

def build_race_results_caches(DB, params):
    global FULL_RESULTS_CACHE
    FULL_RESULTS_CACHE = False
    token = monotonic()

    race = Database.SavedRaceMeta.query.get(params['race_id'])
    heat = Database.Heat.query.get(params['heat_id'])
    if heat.class_id != CLASS_ID_NONE:
        race_class = Database.RaceClass.query.get(heat.class_id)

    race.cacheStatus = token
    heat.cacheStatus = token
    if heat.class_id != CLASS_ID_NONE:
        race_class.cacheStatus = token
    Options.set("eventResults_cacheStatus", token)
    DB.session.commit()

    # rebuild race result
    gevent.sleep()
    if race.cacheStatus == token:
        raceResult = build_result_cache(heat_id=params['heat_id'], round_id=params['round_id'])
        race.results = raceResult.results
        race.cacheStatus = raceResult.cacheStatus
        DB.session.commit()

    # rebuild heat summary
    gevent.sleep()
    if heat.cacheStatus == token:
        heatResult = build_result_cache(heat_id=params['heat_id'])
        heat.results = heatResult.results
        heat.cacheStatus = heatResult.cacheStatus
        DB.session.commit()

    # rebuild class summary
    if heat.class_id != CLASS_ID_NONE:
        if race_class.cacheStatus == token:
            gevent.sleep()
            classResult = build_result_cache(class_id=heat.class_id)
            race_class.results = classResult.results
            race_class.cacheStatus = classResult.cacheStatus
            DB.session.commit()

    # rebuild event summary
    gevent.sleep()
    Options.set("eventResults", json.dumps(calc_leaderboard()))
    Options.set("eventResults_cacheStatus", CacheStatus.VALID)

    logger.info('Built result caches: Race {0}, Heat {1}, Class {2}, Event'.format(params['race_id'], params['heat_id'], heat.class_id))

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
            if current_heat and profile_freqs["f"][current_heat.node_index] != FREQUENCY_ID_NONE:
                pilot_ids.append(pilot.id)
                callsigns.append(pilot.callsign)
                nodes.append(current_heat.node_index)
                team_names.append(pilot.team)
                max_laps.append(max_lap)
                current_laps.append(laps)
        else:
            # find hole shots
            holeshot_laps = []
            for race in racelist:
                pilotraces = Database.SavedPilotRace.query \
                    .filter(Database.SavedPilotRace.pilot_id == pilot.id, \
                    Database.SavedPilotRace.race_id == race \
                    ).all()

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
                nodes.append(holeshot_lap.node_index)
                team_names.append(pilot.team)
                max_laps.append(max_lap)
                holeshots.append(holeshot_laps)

    total_time = []
    last_lap = []
    average_lap = []
    fastest_lap = []
    consecutives = []
    fastest_lap_source = []
    consecutives_source = []

    for i, pilot in enumerate(pilot_ids):
        gevent.sleep()
        # Get the total race time for each pilot
        if max_laps[i] is 0:
            total_time.append(0) # Add zero if no laps completed
        else:
            if USE_CURRENT:
                race_total = 0
                for lap in current_laps[i]:
                    race_total += lap['lap_time']

                total_time.append(race_total)

            else:
                stat_query = DB.session.query(DB.func.sum(Database.SavedRaceLap.lap_time)) \
                    .filter(Database.SavedRaceLap.pilot_id == pilot, \
                        Database.SavedRaceLap.deleted != 1, \
                        Database.SavedRaceLap.race_id.in_(racelist))

                total_time.append(stat_query.scalar())

        gevent.sleep()
        # Get the last lap for each pilot (current race only)
        if max_laps[i] is 0:
            last_lap.append(None) # Add zero if no laps completed
        else:
            if USE_CURRENT:
                last_lap.append(current_laps[i][-1]['lap_time'])
            else:
                last_lap.append(None)

        gevent.sleep()
        # Get the average lap time for each pilot
        if max_laps[i] is 0:
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
        if max_laps[i] is 0:
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
    leaderboard = zip(callsigns, max_laps, total_time, average_lap, fastest_lap, team_names, consecutives, fastest_lap_source, consecutives_source, last_lap, pilot_ids, nodes)

    # Reverse sort max_laps x[1], then sort on total time x[2]
    leaderboard_by_race_time = sorted(leaderboard, key = lambda x: (-x[1], x[2]))

    leaderboard_total_data = []
    for i, row in enumerate(leaderboard_by_race_time, start=1):
        leaderboard_total_data.append({
            'position': i,
            'callsign': row[0],
            'laps': row[1],
            'behind': (leaderboard_by_race_time[0][1] - row[1]),
            'total_time': time_format(row[2]),
            'average_lap': time_format(row[3]),
            'fastest_lap': time_format(row[4]),
            'team_name': row[5],
            'consecutives': time_format(row[6]),
            'fastest_lap_source': row[7],
            'consecutives_source': row[8],
            'last_lap': row[9],
            'pilot_id': row[10],
            'node': row[11],
        })

    gevent.sleep()
    # Sort fastest_laps x[4]
    leaderboard_by_fastest_lap = sorted(leaderboard, key = lambda x: (x[4] if x[4] > 0 else float('inf')))

    leaderboard_fast_lap_data = []
    for i, row in enumerate(leaderboard_by_fastest_lap, start=1):
        leaderboard_fast_lap_data.append({
            'position': i,
            'callsign': row[0],
            'total_time': time_format(row[2]),
            'average_lap': time_format(row[3]),
            'fastest_lap': time_format(row[4]),
            'team_name': row[5],
            'consecutives': time_format(row[6]),
            'fastest_lap_source': row[7],
            'consecutives_source': row[8],
            'last_lap': row[9],
            'pilot_id': row[10],
            'node': row[11],
        })

    gevent.sleep()
    # Sort consecutives x[6]
    leaderboard_by_consecutives = sorted(leaderboard, key = lambda x: (x[6] if x[6] > 0 else float('inf')))

    leaderboard_consecutives_data = []
    for i, row in enumerate(leaderboard_by_consecutives, start=1):
        leaderboard_consecutives_data.append({
            'position': i,
            'callsign': row[0],
            'total_time': time_format(row[2]),
            'average_lap': time_format(row[3]),
            'fastest_lap': time_format(row[4]),
            'team_name': row[5],
            'consecutives': time_format(row[6]),
            'fastest_lap_source': row[7],
            'consecutives_source': row[8],
            'last_lap': row[9],
            'pilot_id': row[10],
            'node': row[11],
        })

    leaderboard_output = {
        'by_race_time': leaderboard_total_data,
        'by_fastest_lap': leaderboard_fast_lap_data,
        'by_consecutives': leaderboard_consecutives_data
    }

    if race_format:
        leaderboard_output['meta'] = {
            'win_condition': race_format.win_condition,
            'team_racing_mode': race_format.team_racing_mode,
        }
    else:
        leaderboard_output['meta'] = {
            'win_condition': WinCondition.NONE,
            'team_racing_mode': False
        }

    return leaderboard_output

def time_format(millis):
    '''Convert milliseconds to 00:00.000'''
    if millis is None:
        return None

    millis = int(millis)
    minutes = millis / 60000
    over = millis % 60000
    seconds = over / 1000
    over = over % 1000
    milliseconds = over
    return '{0:01d}:{1:02d}.{2:03d}'.format(minutes, seconds, milliseconds)