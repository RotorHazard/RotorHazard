''' Class ranking method: Laps/Time, Best X rounds '''

import logging
import RHUtils
from RHRace import StartBehavior
from Results import RaceClassRankMethod

logger = logging.getLogger(__name__)

def registerHandlers(args):
    if 'registerFn' in args:
        for method in discover():
            args['registerFn'](method)

def __(arg): # Replaced with outer language.__ during initialize()
    return arg

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('RaceClassRanking_Initialize', 'classrank_register_bestx', registerHandlers, {}, 75, True)
    if '__' in kwargs:
        __ = kwargs['__']

def rank_best_rounds(RHAPI, race_class, args):
    if 'rounds' not in args or not args['rounds'] or int(args['rounds']) < 1:
        return False

    rounds = int(args['rounds'])

    race_format = RHAPI.db.raceformat_by_id(race_class.format_id)
    heats = RHAPI.db.heats_by_class(race_class.id)

    pilotresults = {}
    for heat in heats:
        races = RHAPI.db.races_by_heat(heat.id)

        for race in races:
            race_result = RHAPI.db.race_results(race)

            if race_result:
                for pilotresult in race_result['by_race_time']:
                    if pilotresult['pilot_id'] not in pilotresults:
                        pilotresults[pilotresult['pilot_id']] = []
                    pilotresults[pilotresult['pilot_id']].append(pilotresult)
            else:
                logger.warning("Failed building ranking, race result not available")
                return False

    leaderboard = []
    for pilotresultlist in pilotresults:
        if race_format and race_format.start_behavior == StartBehavior.STAGGERED:
            pilot_result = sorted(pilotresults[pilotresultlist], key = lambda x: (
                -x['laps'], # reverse lap count
                x['total_time_laps_raw'] if x['total_time_laps_raw'] and x['total_time_laps_raw'] > 0 else float('inf') # total time ascending except 0
            ))
        else:
            pilot_result = sorted(pilotresults[pilotresultlist], key = lambda x: (
                -x['laps'], # reverse lap count
                x['total_time_raw'] if x['total_time_raw'] and x['total_time_raw'] > 0 else float('inf') # total time ascending except 0
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

        timeFormat = RHAPI.db.option('timeFormat')
        new_pilot_result['total_time'] = RHUtils.time_format(new_pilot_result['total_time_raw'], timeFormat)
        new_pilot_result['total_time_laps'] = RHUtils.time_format(new_pilot_result['total_time_laps_raw'], timeFormat)

        leaderboard.append(new_pilot_result)

    if race_format and race_format.start_behavior == StartBehavior.STAGGERED:
        # Sort by laps time
        leaderboard = sorted(leaderboard, key = lambda x: (
            -x['laps'], # reverse lap count
            x['total_time_laps_raw'] if x['total_time_laps_raw'] and x['total_time_laps_raw'] > 0 else float('inf') # total time ascending except 0
        ))

        # determine ranking
        last_rank = None
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

        meta = {
            'rank_fields': [{
                'name': 'laps',
                'label': "Laps"
            },{
                'name': 'total_time_laps',
                'label': "Total"
            },{
                'name': 'starts',
                'label': "Starts"
            }]
        }

    else:
        # Sort by race time
        leaderboard = sorted(leaderboard, key = lambda x: (
            -x['laps'], # reverse lap count
            x['total_time_raw'] if x['total_time_raw'] and x['total_time_raw'] > 0 else float('inf') # total time ascending except 0
        ))

        # determine ranking
        last_rank = None
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

        meta = {
            'rank_fields': [{
                'name': 'laps',
                'label': "Laps"
            },{
                'name': 'total_time',
                'label': "Total"
            },{
                'name': 'starts',
                'label': "Starts"
            }]
        }

    return leaderboard, meta

def discover(*_args, **_kwargs):
    # returns array of methods with default arguments
    return [
        RaceClassRankMethod(
            'best_rounds',
            'Laps/Time: Best X Rounds',
            rank_best_rounds,
            {
                'rounds': 3
            },
            [
                {
                    'id': 'rounds',
                    'label': "Number of rounds",
                    'placeholder': '3',
                    'fieldType': 'basic_int',
                },
            ]
        )
    ]
