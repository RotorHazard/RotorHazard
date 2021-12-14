from flask import request
from flask.blueprints import Blueprint
from numpy.random import default_rng

rng = default_rng()

def createBlueprint(PageCache):
    APP = Blueprint('race_generator', __name__)

    @APP.route('/race-generators/random', methods=['GET'])
    def random_get():
        return {
            "parameters": [
                {"name": "class", "label": "Class", "type": "class"},
                {"name": "seats", "label": "Seats", "type": "seats"},
                {"name": "pilots", "type": "pilots"}
            ]
        }

    @APP.route('/race-generators/random', methods=['POST'])
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
        return {'races': heats}

    @APP.route('/race-generators/mains', methods=['GET'])
    def mains_get():
        return {
            "parameters": [
                {"name": "resultsClass", "label": "Results class", "type": "class"},
                {"name": "mainsClass", "label": "Mains class", "type": "class"},
                {"name": "seats", "label": "Seats", "type": "seats"},
            ]
        }

    @APP.route('/race-generators/mains', methods=['POST'])
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
            return {'races': []}

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
        return {'races': mains}

    return APP
