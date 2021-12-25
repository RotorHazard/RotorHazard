from flask import request
from flask.blueprints import Blueprint
from numpy.random import default_rng

rng = default_rng()

def createBlueprint(PageCache):
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
        results_class = data['resultsClass']
        mains_class = data['mainsClass']
        n_seats = int(data['seats'])
        results = PageCache.get_cache()
        leaderboard = None
        if results_class == "Unclassified":
            leaderboard = results['event_leaderboard']
        else:
            for class_results in results['classes'].values():
                if class_results['name'] == results_class:
                    leaderboard = class_results['leaderboard']
                    break
        if leaderboard is None:
            return {'heats': []}

        pilots = leaderboard[leaderboard['meta']['primary_leaderboard']]
        mains = []
        i = 0
        main_letter = 'A'
        while i < len(pilots):
            race_pilots = pilots[i:i+n_seats]
            i += len(race_pilots)
            # assign pilots to seats
            # prioritise freq assignments to higher ranked pilots
            # (an alternate strategy would be to minimize freq changes)
            seats = [None] * n_seats
            available_seats = list(range(n_seats))
            unassigned = []
            for pilot in race_pilots:
                seat_idx = pilot['node']
                if seat_idx < len(seats) and not seats[seat_idx]:
                    seats[seat_idx] = pilot['callsign']
                    available_seats.remove(seat_idx)
                else:
                    unassigned.append(pilot)
            for pilot in unassigned:
                seat_idx = available_seats.pop(0)
                seats[seat_idx] = pilot['callsign']
            mains.append({'name': main_letter+' Main', 'class': mains_class, 'seats': seats})
            main_letter = chr(ord(main_letter) + 1)
        mains.reverse()
        return {'type': 'Mains', 'heats': mains}

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
        results_class = data['resultsClass']
        mains_class = data['mainsClass']
        n_seats = int(data['seats'])
        bracket = int(data['bracket'])
        results = PageCache.get_cache()

        # 1-index based!
        seeding_table = [
            [[3,6,11,14], [2,7,10,15], [4,5,12,13], [1,8,9,16]],
            {'previous_races': 4,
             'race_offset': 5,
             'races': [
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

        leaderboard_positions = [
            (14,1), (14,2), (14,3), (14,4),
            (13,3), (13,4), (12,3), (12,4),
            (10,3), (10,4), (9,3), (9,4),
            (7,3), (7,4), (5,3), (5,4)
        ]

        mains = []
        if bracket == 1:
            seeding = seeding_table[bracket-1]

            leaderboard = None
            if results_class == "Unclassified":
                leaderboard = results['event_leaderboard']
            else:
                for class_results in results['classes'].values():
                    if class_results['name'] == results_class:
                        leaderboard = class_results['leaderboard']
                        break
            if leaderboard is None:
                return {'heats': []}
    
            pilots = leaderboard[leaderboard['meta']['primary_leaderboard']]

            for i, race_seeds in enumerate(seeding):
                seats = [pilots[seed_pos-1]['callsign'] if seed_pos <= len(pilots) else None for seed_pos in race_seeds]
                mains.append({'name': 'Race '+str(i+1), 'class': mains_class, 'seats': seats[:n_seats]})
        elif bracket >= 2 and bracket <= len(seeding_table):
            seeding = seeding_table[bracket-1]
            n_bracket_races = seeding['previous_races']

            results_heats = results['heats']
            all_heats = None
            if results_class == "Unclassified":
                all_heats = [results_heats[heat_id] for heat_id in range(1,len(results_heats)+1)]
            else:
                class_id = None
                for class_results in results['classes'].values():
                    if class_results['name'] == results_class:
                        class_id = class_results['id']
                        break
                if class_id is None:
                    return {'heats': []}
                all_heats = [results_heats[idx] for idx in results['heats_by_class'][class_id]]
            heats = all_heats[-n_bracket_races:]
            race_offset = seeding['race_offset']
            for i, race_seeds in enumerate(seeding['races']):
                seats = []
                for seed_pos in race_seeds:
                    pilot = None
                    if seed_pos[0] <= len(heats):
                        heat = heats[seed_pos[0]-1]
                        leaderboard = heat['leaderboard']
                        pilots = leaderboard[leaderboard['meta']['primary_leaderboard']]
                        if seed_pos[1] <= len(pilots):
                            pilot = pilots[seed_pos[1]-1]['callsign']
                    seats.append(pilot)
                mains.append({'name': 'Race '+str(i+race_offset), 'class': mains_class, 'seats': seats[:n_seats]})
    
        return {'type': 'MultiGP bracket '+str(bracket), 'heats': mains}

    return APP
