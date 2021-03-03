# JSON API
import json
from sqlalchemy.ext.declarative import DeclarativeMeta
from flask.blueprints import Blueprint

class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
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

def createBlueprint(Database, RHData, Results, RACE, serverInfo, getCurrentProfile):
    DB = Database.DB
    APP = Blueprint('json', __name__)

    @APP.route('/api/pilot/all')
    def api_pilot_all():
        pilots = Database.Pilot.query.all()
        payload = []
        for pilot in pilots:
            payload.append(pilot)

        return json.dumps({"pilots": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/pilot/<int:pilot_id>')
    def api_pilot(pilot_id):
        pilot = Database.Pilot.query.get(pilot_id)

        return json.dumps({"pilot": pilot}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/heat/all')
    def api_heat_all():
        all_heats = {}
        for heat in Database.Heat.query.all():
            heat_id = heat.id
            note = heat.note
            race_class = heat.class_id

            heatnodes = Database.HeatNode.query.filter_by(heat_id=heat.id).all()
            pilots = {}
            for pilot in heatnodes:
                pilots[pilot.node_index] = pilot.pilot_id

            has_race = Database.SavedRaceMeta.query.filter_by(heat_id=heat.id).first()

            if has_race:
                locked = True
            else:
                locked = False

            all_heats[heat_id] = {
                'note': note,
                'heat_id': heat_id,
                'class_id': race_class,
                'nodes_pilots': pilots,
                'locked': locked
            }

        return json.dumps({"heats": all_heats}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/heat/<int:heat_id>')
    def api_heat(heat_id):
        heat = Database.Heat.query.get(heat_id)
        if heat:
            note = heat.note
            race_class = heat.class_id

            heatnodes = Database.HeatNode.query.filter_by(heat_id=heat.id).all()
            pilots = {}
            for pilot in heatnodes:
                pilots[pilot.node_index] = pilot.pilot_id

            has_race = Database.SavedRaceMeta.query.filter_by(heat_id=heat.id).first()

            if has_race:
                locked = True
            else:
                locked = False

            heat = {
                'note': note,
                'heat_id': heat_id,
                'class_id': race_class,
                'nodes_pilots': pilots,
                'locked': locked
            }
        else:
            heat = None

        payload = {
            'setup': heat,
            'leaderboard': Results.calc_leaderboard(RHData, heat_id=heat_id)
        }

        return json.dumps({"heat": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/class/all')
    def api_class_all():
        race_classes = Database.RaceClass.query.all()
        payload = []
        for race_class in race_classes:
            payload.append(race_class)

        return json.dumps({"classes": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/class/<int:class_id>')
    def api_class(class_id):
        race_class = Database.RaceClass.query.get(class_id)

        return json.dumps({"class": race_class}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/format/all')
    def api_format_all():
        formats = Database.RaceFormat.query.all()
        payload = []
        for race_format in formats:
            payload.append(race_format)

        return json.dumps({"formats": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/format/<int:format_id>')
    def api_format(format_id):
        raceformat = Database.RaceFormat.query.get(format_id)

        return json.dumps({"format": raceformat}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/profile/all')
    def api_profile_all():
        profiles = Database.Profiles.query.all()
        payload = []
        for profile in profiles:
            payload.append(profile)

        return json.dumps({"profiles": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/profile/<int:profile_id>')
    def api_profile(profile_id):
        profile = Database.Profiles.query.get(profile_id)

        return json.dumps({"profile": profile}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/race/current')
    def api_race_current():
        if RACE.cacheStatus == Results.CacheStatus.VALID:
            results = RACE.results
        else:
            results = Results.calc_leaderboard(RHData, current_race=RACE, current_profile=getCurrentProfile())
            RACE.results = results
            RACE.cacheStatus = Results.CacheStatus.VALID

        payload = {
            "raw_laps": RACE.node_laps,
            "leaderboard": results
        }

        return json.dumps({"race": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/race/all')
    def api_race_all():
        heats = []
        for heat in Database.SavedRaceMeta.query.with_entities(Database.SavedRaceMeta.heat_id).distinct().order_by(Database.SavedRaceMeta.heat_id):
            max_rounds = DB.session.query(DB.func.max(Database.SavedRaceMeta.round_id)).filter_by(heat_id=heat.heat_id).scalar()
            heats.append({
                "id": heat.heat_id,
                "rounds": max_rounds
            })

        payload = {
            "heats": heats,
            "leaderboard": Results.calc_leaderboard(RHData)
        }

        return json.dumps({"races": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/race/<int:heat_id>/<int:round_id>')
    def api_race(heat_id, round_id):
        race = Database.SavedRaceMeta.query.filter_by(heat_id=heat_id, round_id=round_id).one()

        pilotraces = []
        for pilotrace in Database.SavedPilotRace.query.filter_by(race_id=race.id).all():
            laps = []
            for lap in Database.SavedRaceLap.query.filter_by(pilotrace_id=pilotrace.id).all():
                laps.append({
                        'id': lap.id,
                        'lap_time_stamp': lap.lap_time_stamp,
                        'lap_time': lap.lap_time,
                        'lap_time_formatted': lap.lap_time_formatted,
                        'source': lap.source,
                        'deleted': lap.deleted
                    })

            pilot_data = Database.Pilot.query.filter_by(id=pilotrace.pilot_id).first()
            if pilot_data:
                nodepilot = pilot_data.callsign
            else:
                nodepilot = None

            if RHData.get_option('pilotSort') == 'callsign':
                pilot_data.sort(key=lambda x: (x['callsign'], x['name']))
            else:
                pilot_data.sort(key=lambda x: (x['name'], x['callsign']))

            pilotraces.append({
                'callsign': nodepilot,
                'pilot_id': pilotrace.pilot_id,
                'node_index': pilotrace.node_index,
                'laps': laps
            })
        payload = {
            'start_time_formatted': race.start_time_formatted,
            'nodes': pilotraces,
            'sort': RHData.get_option('pilotSort'),
            'leaderboard': Results.calc_leaderboard(RHData, heat_id=heat_id, round_id=round_id)
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
                "current_heat": RACE.current_heat,
                "num_nodes": RACE.num_nodes,
                "race_status": RACE.race_status,
                "currentProfile": RHData.get_option('currentProfile'),
                "currentFormat": RHData.get_option('currentFormat'),
            }
        }

        return json.dumps({"status": data}), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    @APP.route('/api/options')
    def api_options():
        opt_query = Database.GlobalSettings.query.all()
        options = {}
        if opt_query:
            for opt in opt_query:
                options[opt.option_name] = opt.option_value

            payload = options
        else:
            payload = None

        return json.dumps({"options": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    return APP
