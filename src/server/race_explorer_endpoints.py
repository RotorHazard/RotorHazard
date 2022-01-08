from flask import request, json
from flask.blueprints import Blueprint
from .RHUtils import VTX_TABLE
from . import web
from . import race_explorer_core as core


def createBlueprint(rhconfig, TIMER_ID, INTERFACE, RHData, rhserver):
    APP = Blueprint('race_explorer', __name__, static_url_path='/race-explorer', static_folder='../../race-explorer/build')

    @APP.route('/mqttConfig')
    def mqtt_config():
        return {
            'timerAnnTopic': rhconfig.MQTT['TIMER_ANN_TOPIC'],
            'timerCtrlTopic': rhconfig.MQTT['TIMER_CTRL_TOPIC'],
            'raceAnnTopic': rhconfig.MQTT['RACE_ANN_TOPIC'],
            'sensorAnnTopic': rhconfig.MQTT['SENSOR_ANN_TOPIC']
        }

    @APP.route('/raceResults')
    def race_results():
        """
        Return race results.
        ---
        responses:
            200:
                description: Race results
                content:
                    application/json:
                        schema:
                            $ref: static/schemas/race-results.json
                    application/jsonl:
                        schema:
                            $ref: static/schemas/race-result.json
        """
        if 'application/json' in request.accept_mimetypes:
            return race_results_json()
        elif 'application/jsonl' in request.accept_mimetypes:
            return race_results_jsonl()
        else:
            return '', 406

    @APP.route('/raceResults.jsonl')
    def race_results_jsonl():
        msgs = core.export_results(RHData)
        return '\n'.join([json.dumps(msg) for msg in msgs]), 200, {'Content-Type': 'application/jsonl'}

    @APP.route('/raceResults.json')
    def race_results_json():
        msgs = core.export_results(RHData)
        results = core.pilot_results(msgs)
        return results, 200, {'Content-Type': 'application/json'}

    @APP.route('/raceMetrics')
    def race_metrics_get():
        msgs = core.export_results(RHData)
        results = core.pilot_results(msgs)
        event_data = core.export_event(RHData)
        results = core.calculate_metrics(results, event_data)
        return results, 200, {'Content-Type': 'application/json'}

    @APP.route('/raceMetrics', methods=['POST'])
    def race_metrics_post():
        results = request.get_json()
        event_data = core.export_event(RHData)
        results = core.calculate_metrics(results, event_data)
        return results, 200, {'Content-Type': 'application/json'}

    @APP.route('/eventLeaderboard')
    def event_leaderboard():
        leaderboard = core.export_leaderboard(RHData)
        return leaderboard, 200, {'Content-Type': 'application/json'}

    @APP.route('/raceEvent')
    def race_event_get():
        """
        Return event setup.
        ---
        responses:
            200:
                description: Event setup
                content:
                    application/json:
                        schema:
                            $ref: static/schemas/race-event.json
        """
        data = core.export_event(RHData)
        return data

    @APP.route('/raceEvent', methods=['PUT'])
    def race_event_put():
        """
        Sets event info.
        ---
        requestBody:
           content:
                application/json:
                    schema:
                        $ref: static/schemas/race-event.json
        """
        data = request.get_json()
        core.import_event(data, rhserver)
        return '', 204

    @APP.route('/raceEvent', methods=['POST'])
    def race_event_post():
        if 'sync' in request.args:
            web.sync_event(rhserver)
            data = core.export_event(RHData)
            return data

    @APP.route("/raceClasses")
    def race_classes_get():
        """
        Gets race classes.
        ---
        requestBody:
            content:
             application/json: {}
        """
        race_formats_by_id = {0: 'Free'}
        for race_format in RHData.get_raceFormats():
            race_formats_by_id[race_format.id] = race_format.name

        roots = {}
        rhroots = [rhraceclass for rhraceclass in RHData.get_raceClasses() if rhraceclass.parent_id is None]
        raceclasses_by_id = {}
        q = []
        q.extend(rhroots)
        while q:
            rhraceclass = q.pop()

            raceclass = {'description': rhraceclass.description, 'children': {}}
            raceclass['format'] = race_formats_by_id[rhraceclass.format_id]
            raceclasses_by_id[rhraceclass.id] = raceclass
            if rhraceclass.parent_id:
                parent_raceclass = raceclasses_by_id[rhraceclass.parent_id]
                children = parent_raceclass['children']
            else:
                children = roots
            children[rhraceclass.name] = raceclass

            q.extend(rhraceclass.children)
        return {'classes': roots}

    @APP.route("/raceClasses", methods=['PUT'])
    def race_classes_put():
        """
        Sets race classes.
        ---
        requestBody:
            content:
                application/json: {}
        """
        data = request.get_json()
        existing_race_class_names = set()
        rhraceclasses_by_name = {}
        for rhraceclass in RHData.get_raceClasses():
            existing_race_class_names.add(rhraceclass.name)
            rhraceclasses_by_name[rhraceclass.name] = rhraceclass

        q = []
        def addNodes(children, parent_id):
            q.extend(children)
            for race_class_name, race_class in children:
                rhraceclass = rhraceclasses_by_name.get(race_class_name)
                if rhraceclass:
                    RHData.alter_raceClass({'id': rhraceclass.id,
                                            'name': race_class_name,
                                            'description': race_class['description'],
                                            'parent_id': parent_id})
                    existing_race_class_names.remove(race_class_name)
                else:
                    rhraceclass = RHData.add_raceClass(init={
                                                'name': race_class_name,
                                                'description': race_class['description'],
                                                'parent_id': parent_id})
                    rhraceclasses_by_name[race_class_name] = rhraceclass

        addNodes(data['classes'].items(), None)
        while q:
            race_class_name, race_class = q.pop()
            rhraceclass = rhraceclasses_by_name[race_class_name]
            addNodes(race_class['children'].items(), rhraceclass.id)

        for race_class_name in existing_race_class_names:
            rhraceclass = rhraceclasses_by_name[race_class_name]
            if rhraceclass:
                RHData.delete_raceClass(rhraceclass.id)

        return '', 204

    @APP.route('/trackLayout')
    def track_layout_get():
        """
        Return track layout.
        ---
        responses:
            200:
                description: Track layout
                content:
                    application/json:
                        schema:
                            $ref: static/schemas/race-track.json
        """
        track = RHData.get_optionJson('trackLayout')
        if not track or not track.get('locationType') or not track.get('layout'):
            track = rhserver['DEFAULT_TRACK']
            RHData.set_optionJson('trackLayout', track)
        return track

    @APP.route('/trackLayout', methods=['PUT'])
    def track_layout_put():
        """
        Sets track layout.
        ---
        requestBody:
            content:
                application/json:
                    schema:
                        $ref: static/schemas/race-track.json
        """
        data = request.get_json()
        RHData.set_optionJson('trackLayout', data)
        return '', 204

    @APP.route('/pilots')
    def pilots_get():
        rhpilots = RHData.get_pilots()
        pilots = {}
        for rhpilot in rhpilots:
            pilots[rhpilot.callsign] = {
                'name': rhpilot.name,
                'url': rhpilot.url
            }
        return {'pilots': pilots}

    @APP.route('/pilots', methods=['PUT'])
    def pilots_put():
        data = request.get_json()
        existing_pilot_callsigns = set()
        rhpilots_by_callsign = {}
        for rhpilot in RHData.get_pilots():
            existing_pilot_callsigns.add(rhpilot.callsign)
            rhpilots_by_callsign[rhpilot.callsign] = rhpilot

        for callsign, pilot_data in data['pilots'].items():
            rhpilot = rhpilots_by_callsign.get(callsign)
            if rhpilot:
                RHData.alter_pilot({'pilot_id': rhpilot.id,
                                        'callsign': callsign,
                                        'name': pilot_data['name']})
                existing_pilot_callsigns.remove(callsign)
            else:
                rhpilot = RHData.add_pilot(init={
                                            'callsign': callsign,
                                            'name': pilot_data['name']})
                rhpilots_by_callsign[callsign] = rhpilot

        for callsign in existing_pilot_callsigns:
            rhpilot = rhpilots_by_callsign[callsign]
            if rhpilot:
                RHData.delete_pilot(rhpilot.id)

        return '', 204

    @APP.route('/timerMapping')
    def timer_mapping_get():
        timerMapping = RHData.get_optionJson('timerMapping')
        if not timerMapping:
            timerMapping = {
                TIMER_ID: {
                    nm.addr: [{'location': 'Start/finish', 'seat': node.index} for node in nm.nodes]
                    for nm in INTERFACE.node_managers
                }
            }
            RHData.set_optionJson('timerMapping', timerMapping)
        return timerMapping

    @APP.route('/timerMapping', methods=['PUT'])
    def timer_mapping_put():
        data = request.get_json()
        RHData.set_optionJson('timerMapping', data)
        return '', 204

    @APP.route('/timerSetup')
    def timer_setup():
        """
        Return timer setup.
        ---
        responses:
            200:
                description: Timer setup
                content:
                    application/jsonl: {}
        """
        if 'application/jsonl' in request.accept_mimetypes:
            return timer_setup_jsonl()
        else:
            return '', 406
 
    @APP.route('/timerSetup.jsonl')
    def timer_setup_jsonl():
        msgs = []
        for node_manager in INTERFACE.node_managers:
            msg = {'timer': TIMER_ID, 'nodeManager': node_manager.addr, 'type': node_manager.__class__.TYPE}
            msgs.append(msg)
            for node in node_manager.nodes:
                msg = {'timer': TIMER_ID, 'nodeManager': node_manager.addr, 'node': node.multi_node_index, 'frequency': node.frequency}
                if node.bandChannel is not None:
                    msg['bandChannel'] = node.bandChannel
                if node.enter_at_level is not None:
                    msg['enterTrigger'] = node.enter_at_level
                if node.exit_at_level is not None:
                    msg['exitTrigger'] = node.exit_at_level
                if hasattr(node, 'threshold') and node.threshold is not None:
                    msg['threshold'] = node.threshold
                if hasattr(node, 'gain') and node.gain is not None:
                    msg['gain'] = node.gain
                msgs.append(msg)
        return '\n'.join([json.dumps(msg) for msg in msgs]), 200, {'Content-Type': 'application/jsonl'}

    @APP.route('/vtxTable')
    def vtx_table():
        return VTX_TABLE

    return APP
