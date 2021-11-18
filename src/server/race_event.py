import json
from flask.blueprints import Blueprint

def createBlueprint(RHData):
    APP = Blueprint('race_event', __name__, static_url_path='/race-explorer', static_folder='../../race-explorer/build')

    @APP.route('/raceEvent')
    def race_event():
        eventName = RHData.get_option('eventName', '')
        content = ""
        for race in RHData.get_savedRaceMetas():
            round_id = race.round_id
            heat_id = race.heat_id
            pilotraces = RHData.get_savedPilotRaces_by_savedRaceMeta(race.id)
            for pilotrace in pilotraces:
                pilot = RHData.get_pilot(pilotrace.pilot_id)
                pilotlaps = RHData.get_savedRaceLaps_by_savedPilotRace(pilotrace.id)
                laps = [{'lap': i, 'timestamp': pilotlap.lap_time_stamp, 'gate': 'start/finish'} for i,pilotlap in enumerate(pilotlaps)]
                msg = {'event': eventName, 'round': round_id, 'heat': heat_id, 'pilot': pilot.name, 'laps': laps}
                content += json.dumps(msg)
                content += "\n"
        return content

    return APP

