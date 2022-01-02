from flask import request
from flask.blueprints import Blueprint
from numpy.random import default_rng
from . import race_explorer_core as racex

rng = default_rng()

def createBlueprint(RHData):
    APP = Blueprint('heat_generator', __name__)

    @APP.route('/heat-generators/random')
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

    @APP.route('/heat-generators/mains')
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
        stage_leaderboard = stage['leaderboards'].get(results_class)
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

    @APP.route('/heat-generators/mgp-brackets')
    def mgp_brackets_get():
        return {
            "parameters": [
                {"name": "resultsClass", "label": "Results class", "type": "class"},
                {"name": "mainsClass", "label": "Mains class", "type": "class"},
                {"name": "bracket", "label": "Bracket", "type": "integer", "default": 1, "min": 1, "max": 6}
            ]
        }

    @APP.route('/heat-generators/mgp-brackets', methods=['POST'])
    def mgp_brackets_post():
        data = request.get_json()
        stage_idx = data['stage']
        results_class = data['resultsClass']
        mains_class = data['mainsClass']
        bracket = int(data['bracket'])
        leaderboards = racex.export_leaderboard(RHData)
        return mgp_brackets(leaderboards, stage_idx, results_class, mains_class, bracket)

    @APP.route('/heat-generators/fai-single-16')
    def fai_single_16_get():
        return {
            "parameters": [
                {"name": "resultsClass", "label": "Results class", "type": "class"},
                {"name": "mainsClass", "label": "Mains class", "type": "class"},
                {"name": "bracket", "label": "Bracket", "type": "integer", "default": 1, "min": 1, "max": 3}
            ]
        }

    @APP.route('/heat-generators/fai-single-16', methods=['POST'])
    def fai_single_16_post():
        data = request.get_json()
        stage_idx = data['stage']
        results_class = data['resultsClass']
        mains_class = data['mainsClass']
        bracket = int(data['bracket'])
        leaderboards = racex.export_leaderboard(RHData)
        return fai_single_brackets_16(leaderboards, stage_idx, results_class, mains_class, bracket)

    @APP.route('/heat-generators/fai-double-16')
    def fai_double_16_get():
        return {
            "parameters": [
                {"name": "resultsClass", "label": "Results class", "type": "class"},
                {"name": "mainsClass", "label": "Mains class", "type": "class"},
                {"name": "bracket", "label": "Bracket", "type": "integer", "default": 1, "min": 1, "max": 6}
            ]
        }

    @APP.route('/heat-generators/fai-double-16', methods=['POST'])
    def fai_double_16_post():
        data = request.get_json()
        stage_idx = data['stage']
        results_class = data['resultsClass']
        mains_class = data['mainsClass']
        bracket = int(data['bracket'])
        leaderboards = racex.export_leaderboard(RHData)
        return fai_double_brackets_16(leaderboards, stage_idx, results_class, mains_class, bracket)

    return APP


def mgp_brackets(leaderboards, stage_idx, results_class, mains_class, bracket):
    '''
    2021 MultiGP Rules & Regulations
    7.9.1. Double Elimination Brackets
    https://docs.google.com/document/d/1x-otorbEruq5oD6b1yzoBTHO9SwUNmb2itguUoY8x3s/
    As per the diagram
    https://www.multigp.com/wp-content/uploads/2019/04/multigp-double-elim-brackets1.png
    '''

    # 1-index based!
    seeding_table = [
        [[4,7,11,13], [3,6,10,14], [2,5,9,15], [1,8,12,16]],
        {'previous_races': 4,
         'race_offset': 5,
         'races': [
             # (race, position)
             [(1,3),(2,3),(1,4),(2,4)],
             [(1,2),(2,1),(1,1),(2,2)],
             [(3,4),(4,4),(3,3),(4,3)],
             [(3,1),(4,2),(3,2),(4,1)]
             ]
        },
        {'previous_races': 4,
         'race_offset': 9,
         'races': [
             [(5,1),(5,2),(7,1),(7,2)],
             [(6,3),(6,4),(8,3),(8,4)],
             [(6,1),(6,2),(8,1),(8,2)],
             ]
        },
        {'previous_races': 3,
         'race_offset': 12,
         'races': [
             [(9,1),(9,2),(10,1),(10,2)]
             ]
        },
        {'previous_races': 2,
         'race_offset': 13,
         'races': [
             [(12,1),(12,2),(11,3),(11,4)]
             ]
        },
        {'previous_races': 3,
         'race_offset': 14,
         'races': [
             [(11,1),(11,2),(13,1),(13,2)]
             ]
        }
    ]
    leaderboard_positions = [
        (14,1), (14,2), (14,3), (14,4),
        (13,3), (13,4), (12,3), (12,4),
        (10,3), (10,4), (9,3), (9,4),
        (5,3), (5,4), (7,3), (7,4)
    ]
    return brackets(leaderboards, stage_idx, results_class, mains_class, bracket, seeding_table, leaderboard_positions)


def fai_single_brackets_16(leaderboards, stage_idx, results_class, mains_class, bracket):
    '''
    https://www.fai.org/sites/default/files/ciam/wcup_drones/sc4_vol_f9_dronesport_2021.pdf
    '''

    # 1-index based!
    seeding_table = [
        [[16,1,8,9], [13,4,5,12], [14,3,6,10], [15,2,7,11]],
        {'previous_races': 4,
         'race_offset': 5,
         'races': [
             # (race, position)
             [(1,2),(1,1),(2,1),(2,2)],
             [(3,2),(3,1),(4,1),(4,2)]
             ]
        },
        {'previous_races': 2,
         'race_offset': 7,
         'races': [
             [(5,4),(5,3),(6,3),(6,4)],
             [(5,2),(5,1),(6,1),(6,2)],
             ]
        }
    ]
    leaderboard_positions = [
        (8,1), (8,2), (8,3), (8,4),
        (7,1), (7,2), (7,3), (7,4)
    ]
    return brackets(leaderboards, stage_idx, results_class, mains_class, bracket, seeding_table, leaderboard_positions)


def fai_double_brackets_16(leaderboards, stage_idx, results_class, mains_class, bracket):
    '''
    https://www.fai.org/sites/default/files/ciam/wcup_drones/sc4_vol_f9_dronesport_2021.pdf
    '''

    # 1-index based!
    seeding_table = [
        [[16,1,8,9], [13,4,5,12], [14,3,6,10], [15,2,7,11]],
        {'previous_races': 4,
         'race_offset': 5,
         'races': [
             # (race, position)
             [(1,4),(2,3),(3,3),(4,4)],
             [(2,4),(1,3),(4,3),(3,4)],
             [(1,2),(1,1),(2,1),(2,2)],
             [(3,2),(3,1),(4,1),(4,2)]
             ]
        },
        {'previous_races': 4,
         'race_offset': 9,
         'races': [
             [(8,4),(6,2),(5,1),(7,3)],
             [(7,4),(5,2),(6,1),(8,3)],
             ]
        },
        {'previous_races': 4,
         'race_offset': 11,
         'races': [
             [(9,2),(9,1),(10,1),(10,2)],
             [(7,2),(7,1),(8,1),(8,2)],
             ]
        },
        {'previous_races': 2,
         'race_offset': 13,
         'races': [
             [(12,4),(11,2),(11,1),(12,3)]
             ]
        },
        {'previous_races': 2,
         'race_offset': 14,
         'races': [
             [(13,2),(12,2),(12,1),(13,1)]
             ]
        }
    ]
    leaderboard_positions = [
        (14,1), (14,2), (14,3), (14,4),
        (13,3), (13,4), (11,3), (11,4)
    ]
    return brackets(leaderboards, stage_idx, results_class, mains_class, bracket, seeding_table, leaderboard_positions)


def brackets(leaderboards, stage_idx, results_class, mains_class, bracket, seeding_table, leaderboard_positions):
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
            mains.append({'name': 'Race '+str(i+1), 'class': mains_class, 'seats': seats})
    elif bracket >= 2 and bracket <= len(seeding_table):
        seeding = seeding_table[bracket-1]
        n_bracket_races = seeding['previous_races']

        heats = racex.get_previous_n_races(stages, stage_idx, [results_class], n_bracket_races)
        if not heats:
            return {'heats': []}

        race_offset = seeding['race_offset']
        heat_offset = race_offset - n_bracket_races
        for i, race_seeds in enumerate(seeding['races']):
            seats = []
            for seed_pos in race_seeds:
                pilot = None
                heat = heats[seed_pos[0]-heat_offset]
                ranking = heat['ranking']
                if seed_pos[1] <= len(ranking):
                    pilot = ranking[seed_pos[1]-1]['pilot']
                seats.append(pilot)
            mains.append({'name': 'Race '+str(i+race_offset), 'class': mains_class, 'seats': seats})
    else:
        raise ValueError("Invalid bracket: {}".format(bracket))

    bracket_heats = {'type': 'Bracket '+str(bracket), 'heats': mains}
    if bracket == len(seeding_table):
        bracket_heats['leaderboards'] = {mains_class: {'method': 'heatPositions', 'heatPositions': leaderboard_positions}}
    return bracket_heats


def get_previous_stage(stages, stage_idx, race_class_name):
    if stage_idx-1 < 0 or stage_idx-1 >= len(stages):
        return None

    for i in range(stage_idx-1, -1, -1):
        stage = stages[i]
        if race_class_name in stage['leaderboards']:
            return stage

    return None

