# JSON API
import json
import Results
from sqlalchemy.ext.declarative import DeclarativeMeta
from flask.blueprints import Blueprint

class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):  #pylint: disable=arguments-differ
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                if field != "query" \
                    and field != "query_class":
                    try:
                        json.dumps(data) # this will fail on non-encodable values, like other classes
                        if field == "frequencies":
                            fields[field] = json.loads(data)["f"]
                        elif field == "enter_ats" or field == "exit_ats":
                            fields[field] = json.loads(data)["v"]
                        else:
                            fields[field] = data
                    except TypeError:
                        fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)

def createBlueprint(RaceContext, serverInfo):
    APP = Blueprint('json', __name__)

    @APP.route('/api/pilot/all')
    def api_pilot_all():
        pilots = RaceContext.rhdata.get_pilots()
        payload = []
        for pilot in pilots:
            payload.append(pilot)

        return json.dumps({"pilots": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/pilot/<int:pilot_id>')
    def api_pilot(pilot_id):
        pilot = RaceContext.rhdata.get_pilot(pilot_id)

        return json.dumps({"pilot": pilot}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/heat/all')
    def api_heat_all():
        all_heats = {}
        for heat in RaceContext.rhdata.get_heats():
            heat_id = heat.id
            displayname = heat.display_name
            race_class = heat.class_id

            heatnodes = RaceContext.rhdata.get_heatNodes_by_heat(heat.id)
            pilots = {}
            for pilot in heatnodes:
                pilots[pilot.node_index] = pilot.pilot_id

            locked = RaceContext.rhdata.savedRaceMetas_has_heat(heat.id)

            all_heats[heat_id] = {
                'displayname': displayname,
                'heat_id': heat_id,
                'class_id': race_class,
                'nodes_pilots': pilots,
                'locked': locked
            }

        return json.dumps({"heats": all_heats}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/heat/<int:heat_id>')
    def api_heat(heat_id):
        heat = RaceContext.rhdata.get_heat(heat_id)
        if heat:
            displayname = heat.display_name
            race_class = heat.class_id

            heatnodes = RaceContext.rhdata.get_heatNodes_by_heat(heat.id)
            pilots = {}
            for pilot in heatnodes:
                pilots[pilot.node_index] = pilot.pilot_id

            locked = RaceContext.rhdata.savedRaceMetas_has_heat(heat.id)

            heat = {
                'displayname': displayname,
                'heat_id': heat_id,
                'class_id': race_class,
                'nodes_pilots': pilots,
                'locked': locked
            }
        else:
            heat = None

        payload = {
            'setup': heat,
            'leaderboard': Results.calc_leaderboard(RaceContext, heat_id=heat_id)
        }

        return json.dumps({"heat": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/class/all')
    def api_class_all():
        race_classes = RaceContext.rhdata.get_raceClasses()
        payload = []
        for race_class in race_classes:
            payload.append(race_class)

        return json.dumps({"classes": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/class/<int:class_id>')
    def api_class(class_id):
        race_class = RaceContext.rhdata.get_raceClass(class_id)

        return json.dumps({"class": race_class}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/format/all')
    def api_format_all():
        formats = RaceContext.rhdata.get_raceFormats()
        payload = []
        for race_format in formats:
            payload.append(race_format)

        return json.dumps({"formats": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/format/<int:format_id>')
    def api_format(format_id):
        raceformat = RaceContext.rhdata.get_raceFormat(format_id)

        return json.dumps({"format": raceformat}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/profile/all')
    def api_profile_all():
        profiles = RaceContext.rhdata.get_profiles()
        payload = []
        for profile in profiles:
            payload.append(profile)

        return json.dumps({"profiles": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/profile/<int:profile_id>')
    def api_profile(profile_id):
        profile = RaceContext.rhdata.get_profile(profile_id)

        return json.dumps({"profile": profile}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/race/current')
    def api_race_current():
        results = RaceContext.race.get_results()

        payload = {
            "raw_laps": RaceContext.race.node_laps,
            "leaderboard": results
        }

        return json.dumps({"race": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/race/all')
    def api_race_all():
        heats = []
        for heat in RaceContext.rhdata.get_heats():
            max_rounds = RaceContext.rhdata.get_max_round(heat.id)
            heats.append({
                "id": heat.id,
                "rounds": max_rounds
            })

        payload = {
            "heats": heats,
            "leaderboard": Results.calc_leaderboard(RaceContext)
        }

        return json.dumps({"races": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/race/<int:heat_id>/<int:round_id>')
    def api_race(heat_id, round_id):
        race = RaceContext.rhdata.get_savedRaceMeta_by_heat_round(heat_id, round_id)

        pilotraces = []
        for pilotrace in RaceContext.rhdata.get_savedPilotRaces_by_savedRaceMeta(race.id):
            laps = []
            for lap in RaceContext.rhdata.get_savedRaceLaps_by_savedPilotRace(pilotrace.id):
                laps.append({
                        'id': lap.id,
                        'lap_time_stamp': lap.lap_time_stamp,
                        'lap_time': lap.lap_time,
                        'lap_time_formatted': lap.lap_time_formatted,
                        'source': lap.source,
                        'deleted': lap.deleted
                    })

            pilot_data = RaceContext.rhdata.get_pilot(pilotrace.pilot_id)
            if pilot_data:
                nodepilot = pilot_data.callsign
            else:
                nodepilot = None

            pilotraces.append({
                'callsign': nodepilot,
                'pilot_id': pilotrace.pilot_id,
                'node_index': pilotrace.node_index,
                'laps': laps
            })
        payload = {
            'start_time_formatted': race.start_time_formatted,
            'nodes': pilotraces,
            'sort': RaceContext.serverconfig.get_item('UI', 'pilotSort'),
            'leaderboard': Results.calc_leaderboard(RaceContext, heat_id=heat_id, round_id=round_id)
        }

        return json.dumps({"race": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/status')
    def api_status():
        data = {
            "server_info": {
                "server_api": serverInfo['server_api'],
                "json_api": serverInfo['json_api'],
                "node_api_best": serverInfo['node_api_best'],
                "release_version": serverInfo['release_version'],
                "node_api_match": serverInfo['node_api_match'],
                "node_api_lowest": serverInfo['node_api_lowest'],
                "node_api_levels": serverInfo['node_api_levels']
            },
            "state": {
                "current_heat": RaceContext.race.current_heat,
                "num_nodes": RaceContext.race.num_nodes,
                "race_status": RaceContext.race.race_status,
                "currentProfile": RaceContext.rhdata.get_option('currentProfile'),
                "currentFormat": RaceContext.rhdata.get_option('currentFormat'),
                "currentHeat": RaceContext.rhdata.get_option('currentHeat'),
            }
        }

        return json.dumps({"status": data}), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/options')
    def api_options():
        opt_query = RaceContext.rhdata.get_options()
        options = {}
        if opt_query:
            for opt in opt_query:
                if opt.option_name not in ['eventResults', 'secret_key']:
                    options[opt.option_name] = opt.option_value

            payload = options
        else:
            payload = None

        return json.dumps({"options": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    return APP
