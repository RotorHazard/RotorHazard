''' Class ranking method: Cumulative points from all heats '''

import logging
import RHUtils
from eventmanager import Evt
from RHRace import StartBehavior
from Results import RaceClassRankMethod
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

def rank_points_total(rhapi, race_class, args):

    heats = rhapi.db.heats_by_class(race_class.id)

    pilotresults = {}
    for heat in heats:
        races = rhapi.db.races_by_heat(heat.id)

        for race in races:
            race_result = rhapi.db.race_results(race)

            if race_result:
                for pilotresult in race_result[race_result['meta']['primary_leaderboard']]:
                    if pilotresult['pilot_id'] not in pilotresults:
                        pilotresults[pilotresult['pilot_id']] = []
                    pilotresults[pilotresult['pilot_id']].append(pilotresult)
            else:
                logger.warning("Failed building ranking, race result not available")
                return False, {}

    leaderboard = []
    for pilotresultlist in pilotresults:
        pilot_result = pilotresults[pilotresultlist]

        new_pilot_result = {}
        new_pilot_result['pilot_id'] = pilot_result[0]['pilot_id']
        new_pilot_result['callsign'] = pilot_result[0]['callsign']
        new_pilot_result['team_name'] = pilot_result[0]['team_name']
        new_pilot_result['points'] = 0

        for race in pilot_result:
            if 'points' in race:
                new_pilot_result['points'] += race['points']

        leaderboard.append(new_pilot_result)

    # Sort by points
    if 'ascending' in args and args['ascending']:
        leaderboard = sorted(leaderboard, key = lambda x: (
            x['points']
        ))
    else:
        leaderboard = sorted(leaderboard, key = lambda x: (
            -x['points']
        ))

    # determine ranking
    last_rank = None
    last_rank_points = 0
    for i, row in enumerate(leaderboard, start=1):
        pos = i
        if last_rank_points == row['points']:
            pos = last_rank
        last_rank = pos
        last_rank_points = row['points']

        row['position'] = pos

    meta = {
        'rank_fields': [{
            'name': 'points',
            'label': "Points"
        }]
    }

    return leaderboard, meta

def register_handlers(args):
    args['register_fn'](
        RaceClassRankMethod(
            "Cumulative Points",
            rank_points_total,
            {
                'ascending': False
            },
            [
                UIField('ascending', "Ascending", UIFieldType.CHECKBOX, value=False),
            ]
        )
    )

def initialize(rhapi):
    rhapi.events.on(Evt.CLASS_RANK_INITIALIZE, register_handlers)

