from flask import request
from flask.blueprints import Blueprint
from numpy.random import default_rng

rng = default_rng()

def createBlueprint():
    APP = Blueprint('race_generator', __name__)

    @APP.route('/race-generators/random', methods=['GET'])
    def random_get():
        return {
            "class": {"label": "Class", "type": "class"},
            "seats": {"type": "seats"},
            "pilots": {"type": "pilots"}
        }

    @APP.route('/race-generators/random', methods=['POST'])
    def random_post():
        data = request.get_json()
        race_class = data['class']
        n_seats = int(data['seats'])
        pilots = data['pilots']
        seats = [None] * n_seats
        heats = []
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

    return APP
