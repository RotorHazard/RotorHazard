from flask import request
from flask.blueprints import Blueprint
from numpy.random import default_rng
from . import race_explorer_core as racex

rng = default_rng()

def createBlueprint(RHData):
    APP = Blueprint('heat_generator', __name__)

    @APP.route('/heat-generators/random', methods=['GET'])
    def random_get():
        return {
            "parameters": [
                {"name": "class", "label": "Class", "type": "class"},
                {"name": "seats", "label": "Seats", "type": "seats"},
                {"name": "pilots", "type": "pilots"}
            ]
        }

    @APP.route('/heat-generators/random', methods=['POST'])
    def random_post():
        data = request.get_json()
        race_class = data['class']
        n_seats = int(data['seats'])
        pilots = data['pilots']
        heats = []
        seats = [None] * n_seats
        i = 0
        for pilot in rng.choice(pilots, len(pilots), replace=False):
            seats[i] = pilot
            i += 1
            if i == n_seats:
                heats.append({'name': 'Heat '+str(len(heats)+1), 'class': race_class, 'seats': seats})
                seats = [None] * n_seats
                i = 0
        if i > 0:
            heats.append({'name': 'Heat '+str(len(heats)+1), 'class': race_class, 'seats': seats})
        return {'type': 'Random', 'heats': heats}

    @APP.route('/heat-generators/mains', methods=['GET'])
    def mains_get():
        return {
            "parameters": [
                {"name": "resultsClass", "label": "Results class", "type": "class"},
                {"name": "mainsClass", "label": "Mains class", "type": "class"},
                {"name": "seats", "label": "Seats", "type": "seats"}
            ]
        }

    @APP.route('/heat-generators/mains', methods=['POST'])
    def mains_post():
        data = request.get_json()
        stage_idx = data['stage']
        results_class = data['resultsClass']
        mains_class = data['mainsClass']
        n_seats = int(data['seats'])

        leaderboards = racex.export_leaderboard(RHData)
        stages = leaderboards['stages']
        if stage_idx-1 < 0 or stage_idx-1 >= len(stages):
            return {'heats': []}
        stage = stages[stage_idx-1]
        stage_leaderboard = stage['leaderboards'].get(results_class, None)
        if stage_leaderboard is None:
            return {'heats': []}

        pilots_to_seats = {}
        for heat in stage['heats']:
            for seat_idx, pilot in enumerate(heat['seats']):
                pilots_to_seats[pilot] = seat_idx

        prs = stage_leaderboard['ranking']
        mains = []
        i = 0
        main_letter = 'A'
        while i < len(prs):
            heat_prs = prs[i:i+n_seats]
            i += len(heat_prs)
            # assign pilots to seats
            # prioritise freq assignments to higher ranked pilots
            # (an alternate strategy would be to minimize freq changes)
            seats = [None] * n_seats
            available_seats = list(range(n_seats))
            unassigned = []
            for pr in heat_prs:
                pilot = pr['pilot']
                seat_idx = pilots_to_seats[pilot]
                if seat_idx < len(seats) and not seats[seat_idx]:
                    seats[seat_idx] = pilot
                    available_seats.remove(seat_idx)
                else:
                    unassigned.append(pilot)
            for pilot in unassigned:
                seat_idx = available_seats.pop(0)
                seats[seat_idx] = pilot
            mains.append({'name': main_letter+' Main', 'class': mains_class, 'seats': seats})
            main_letter = chr(ord(main_letter) + 1)
        mains.reverse()
        return {'type': 'Mains', 'heats': mains, 'leaderboards': {mains_class: {'method': 'best'}}}

    @APP.route('/heat-generators/mgp-brackets', methods=['GET'])
    def mgp_brackets_get():
        return {
            "parameters": [
                {"name": "resultsClass", "label": "Results class", "type": "class"},
                {"name": "mainsClass", "label": "Mains class", "type": "class"},
                {"name": "seats", "label": "Seats", "type": "seats"},
                {"name": "bracket", "label": "Bracket", "type": "integer", "default": 1, "min": 1, "max": 6}
            ]
        }

    @APP.route('/heat-generators/mgp-brackets', methods=['POST'])
    def mgp_brackets_post():
        '''
        2021 MultiGP Rules & Regulations
        7.9.1. Double Elimination Brackets
        https://docs.google.com/document/d/1x-otorbEruq5oD6b1yzoBTHO9SwUNmb2itguUoY8x3s/
        '''
        data = request.get_json()
        stage_idx = data['stage']
        results_class = data['resultsClass']
        mains_class = data['mainsClass']
        n_seats = int(data['seats'])
        bracket = int(data['bracket'])

        # 1-index based!
        seeding_table = [
            [[3,6,11,14], [2,7,10,15], [4,5,12,13], [1,8,9,16]],
            {'previous_races': 4,
             'race_offset': 5,
             'races': [
                 # (race, position)
                 [(1,3),(1,4),(2,3),(2,4)],
                 [(1,1),(1,2),(2,1),(2,2)],
                 [(3,3),(3,4),(4,3),(4,4)],
                 [(3,1),(3,2),(4,1),(4,2)]
                 ]
            },
            {'previous_races': 4,
             'race_offset': 9,
             'races': [
                 [(1,1),(1,2),(2,3),(2,4)],
                 [(3,1),(3,2),(4,3),(4,4)],
                 [(2,1),(2,2),(4,1),(4,2)],
                 ]
            },
            {'previous_races': 3,
             'race_offset': 12,
             'races': [
                 [(1,1),(1,2),(2,1),(2,2)]
                 ]
            },
            {'previous_races': 2,
             'race_offset': 13,
             'races': [
                 [(2,1),(2,2),(1,3),(1,4)]
                 ]
            },
            {'previous_races': 3,
             'race_offset': 14,
             'races': [
                 [(1,1),(1,2),(3,1),(3,2)]
                 ]
            }
        ]

        leaderboards = racex.export_leaderboard(RHData)
        stages = leaderboards['stages']

        mains = []
        if bracket == 1:
            stage = get_previous_stage(stages, stage_idx, results_class)
            if not stage:
                return {'heats': []}

            stage_leaderboard = stage['leaderboards'][results_class]
            prs = stage_leaderboard['ranking']

            seeding = seeding_table[bracket-1]
            for i, race_seeds in enumerate(seeding):
                seats = [prs[seed_pos-1]['pilot'] if seed_pos <= len(prs) else None for seed_pos in race_seeds]
                mains.append({'name': 'Race '+str(i+1), 'class': mains_class, 'seats': seats[:n_seats]})
        elif bracket >= 2 and bracket <= len(seeding_table):
            seeding = seeding_table[bracket-1]
            n_bracket_races = seeding['previous_races']

            heats = get_previous_n_races(stages, stage_idx, results_class, n_bracket_races)
            if not heats:
                return {'heats': []}

            race_offset = seeding['race_offset']
            for i, race_seeds in enumerate(seeding['races']):
                seats = []
                for seed_pos in race_seeds:
                    pilot = None
                    heat = heats[seed_pos[0]-1]
                    ranking = heat['ranking']
                    if seed_pos[1] <= len(ranking):
                        pilot = ranking[seed_pos[1]-1]['pilot']
                    seats.append(pilot)
                mains.append({'name': 'Race '+str(i+race_offset), 'class': mains_class, 'seats': seats[:n_seats]})
    
        bracket_heats = {'type': 'MultiGP bracket '+str(bracket), 'heats': mains}
        if bracket == len(seeding_table):
            leaderboard_positions = [
                (14,1), (14,2), (14,3), (14,4),
                (13,3), (13,4), (12,3), (12,4),
                (10,3), (10,4), (9,3), (9,4),
                (7,3), (7,4), (5,3), (5,4)
            ]
            bracket_heats['leaderboards'] = {mains_class: {'method': 'heatPositions', 'heatPositions': leaderboard_positions}}
        return bracket_heats

    return APP


def get_previous_stage(stages, stage_idx, race_class_name):
    if stage_idx-1 < 0 or stage_idx-1 >= len(stages):
        return None

    for i in range(stage_idx-1, -1, -1):
        stage = stages[i]
        if race_class_name in stage['leaderboards']:
            return stage

    return None


def get_previous_n_races(stages, stage_idx, race_class_name, n):
    if stage_idx-1 < 0 or stage_idx-1 >= len(stages):
        return None

    races = []
    for i in range(stage_idx-1, -1, -1):
        stage = stages[i]
        for heat in reversed(stage['heats']):
            if heat.get('class', None) == race_class_name:
                races.append(heat)
                if len(races) == n:
                    return races

    return None
