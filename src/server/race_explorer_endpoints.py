import itertools
import json
from flask import request
from flask.blueprints import Blueprint
from .RHUtils import VTX_TABLE
from . import RHRace
import numpy as np


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
        msgs = export_results(rhserver)
        return '\n'.join([json.dumps(msg) for msg in msgs]), 200, {'Content-Type': 'application/jsonl'}

    @APP.route('/raceResults.json')
    def race_results_json():
        msgs = export_results(rhserver)
        results = pilot_results(msgs)
        return json.dumps(results), 200, {'Content-Type': 'application/json'}

    @APP.route('/raceEvent', methods=['GET'])
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
        event_name = RHData.get_option('eventName', "")
        event_desc = RHData.get_option('eventDescription', "")
        event_url = RHData.get_option('eventURL', "")

        pilots = {}
        pilots_by_id = {}
        for pilot in RHData.get_pilots():
            pilots[pilot.callsign] = {'name': pilot.name}
            pilots_by_id[pilot.id] = pilot

        race_formats = {'Free': {'start': 'first-pass', 'duration': 0}}
        race_formats_by_id = {0: 'Free'}
        for race_format in RHData.get_raceFormats():
            race_formats[race_format.name] = {
                'start': 'start-line' if race_format.start_behavior == RHRace.StartBehavior.FIRST_LAP else 'first-pass',
                'duration': race_format.race_time_sec + race_format.lap_grace_sec
            }
            race_formats_by_id[race_format.id] = race_format.name

        race_classes = {"Unclassified": {'description': "Default class"}}
        race_classes_by_id = {0: "Unclassified"}
        for race_class in RHData.get_raceClasses():
            race_format_name = race_formats_by_id[race_class.format_id]
            race_classes[race_class.name] = {
                'description': race_class.description,
                'format': race_format_name
            }
            race_classes_by_id[race_class.id] = race_class.name

        seats = []
        current_profile = RHData.get_optionInt('currentProfile')
        profile = RHData.get_profile(current_profile)
        freqs = json.loads(profile.frequencies)
        for f_b_c in zip(freqs['f'], freqs['b'], freqs['c']):
            fbc = {'frequency': f_b_c[0]}
            if f_b_c[1] and f_b_c[2]:
                fbc['bandChannel'] = f_b_c[1] + str(f_b_c[2])
            seats.append(fbc)

        event_formats = {}
        event_classes = {}
        stages = []
        prev_stage_name = None
        for heat_idx, heat_data in enumerate(RHData.get_heats()):
            heat_seats = [None] * len(seats)
            for heat_node in RHData.get_heatNodes_by_heat(heat_data.id):
                if heat_node.node_index < len(heat_seats) and heat_node.pilot_id in pilots_by_id:
                    heat_seats[heat_node.node_index] = pilots_by_id[heat_node.pilot_id].callsign
            race_name = heat_data.note if heat_data.note else 'Heat '+str(heat_idx+1)
            race_class_name = race_classes_by_id[heat_data.class_id]
            if race_class_name not in event_classes:
                race_class = race_classes[race_class_name]
                event_classes[race_class_name] = race_class
                race_format_name = race_class['format']
                if race_format_name not in event_formats:
                    event_formats[race_format_name] = race_formats[race_format_name]
            race = {
                'id': str(heat_data.id),
                'name': race_name,
                'class': race_class_name,
                'seats': heat_seats
            }
            stage_name = heat_data.stage.name
            if stage_name != prev_stage_name:
                races = []
                stage = {'id': str(heat_data.stage_id), 'name': stage_name, 'heats': races}
                stages.append(stage)
                prev_stage_name = stage_name
            races.append(race)
        data = {
            'name': event_name,
            'description': event_desc,
            'url': event_url,
            'pilots': pilots,
            'formats': event_formats,
            'classes': event_classes,
            'seats': seats,
            'stages': stages
        }
        return data

    @APP.route('/raceEvent', methods=['PUT'])
    def race_event_post():
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
        import_event(data, rhserver)
        return '', 204

    @APP.route('/trackLayout', methods=['GET'])
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
        track = RHData.get_option('trackLayout', None)
        if track:
            track = json.loads(track)
        if not track or not track['layout']:
            track = rhserver['DEFAULT_TRACK']
            RHData.set_option('trackLayout', json.dumps(track))
        return track

    @APP.route('/trackLayout', methods=['PUT'])
    def track_layout_post():
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
        RHData.set_option('trackLayout', json.dumps(data))
        return '', 204

    @APP.route('/timerMapping', methods=['GET'])
    def timer_mapping_get():
        timerMapping = RHData.get_option('timerMapping', None)
        if timerMapping:
            timerMapping = json.loads(timerMapping)
        else:
            timerMapping = {
                TIMER_ID: {
                    nm.addr: [{'location': 'Start/finish', 'seat': node.index} for node in nm.nodes]
                    for nm in INTERFACE.node_managers
                }
            }
            RHData.set_option('timerMapping', json.dumps(timerMapping))
        return timerMapping

    @APP.route('/timerMapping', methods=['PUT'])
    def timer_mapping_post():
        data = request.get_json()
        RHData.set_option('timerMapping', json.dumps(data))
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


def export_results(rhserver):
    RHData = rhserver['RHData']
    event_name = RHData.get_option('eventName', '')
    msgs = []
    for race in RHData.get_savedRaceMetas():
        race_id = race.id
        round_idx = race.round_id - 1
        heat_id = race.heat_id
        heat = RHData.get_heat(heat_id)
        stage_id = heat.stage_id
        pilotraces = RHData.get_savedPilotRaces_by_savedRaceMeta(race.id)
        for pilotrace in pilotraces:
            pilot = RHData.get_pilot(pilotrace.pilot_id)
            if pilot:
                pilotlaps = RHData.get_savedRaceLaps_by_savedPilotRace(pilotrace.id)
                laps = []
                for lap_id,pilotlap in enumerate(pilotlaps):
                    laps.append({'lap': lap_id, 'timestamp': pilotlap.lap_time_stamp, 'location': 0})
                    lapsplits = RHData.get_lapSplits_by_lap(race_id, pilotrace.node_index, lap_id)
                    for lapsplit in lapsplits:
                        laps.append({'lap': lap_id, 'timestamp': lapsplit.split_time_stamp, 'location': lapsplit.split_id+1})
                msg = {'event': event_name, 'stage': 'id:'+str(stage_id), 'round': round_idx, 'heat': 'id:'+str(heat_id), 'pilot': pilot.callsign, 'laps': laps}
                msgs.append(msg)
    return msgs


def pilot_results(msgs):
    results = {'pilots': {}}
    results_by_pilot = results['pilots']
    for msg in msgs:
        eventName = msg['event']
        stageIdx = msg['stage']
        roundIdx = msg['round']
        heatIdx = msg['heat']
        pilot = msg['pilot']
        if pilot not in results_by_pilot:
            results_by_pilot[pilot] = {'events': {}}
        event_results = results_by_pilot[pilot]['events']
        if eventName not in event_results:
            event_results[eventName] = {'stages': {}}
        event_stages = event_results[eventName]['stages']
        if stageIdx not in event_stages:
            event_stages[stageIdx] = {'heats': {}}
        heats = event_stages[stageIdx]['heats']
        if heatIdx not in heats:
            heats[heatIdx] = {'rounds': []}
        rounds = heats[heatIdx]['rounds']
        while roundIdx >= len(rounds):
            rounds.append(None)
        rounds[roundIdx] = {'laps': msg['laps']}
    return results


def import_event(data, rhserver):
    event_name = data['name']
    race_classes = data['classes'] if 'classes' in data else {}
    seats = data['seats']
    pilots = data['pilots']
    stages = data['stages']

    RHData = rhserver['RHData']
    RHData.set_option('eventName', event_name)
    if 'description' in data:
        RHData.set_option('eventDescription', data['description'])
    if 'url' in data:
        RHData.set_option('eventURL', data['url'])

    profile_data = {'profile_name': event_name,
        'frequencies': {'b': [s['bandChannel'][0] if 'bandChannel' in s else None for s in seats],
                        'c': [int(s['bandChannel'][1]) if 'bandChannel' in s else None for s in seats],
                        'f': [s['frequency'] for s in seats]
                        }
        }
    profile = RHData.upsert_profile(profile_data)

    raceFormat_ids = {}
    for rhraceformat in RHData.get_raceFormats():
        raceFormat_ids[rhraceformat.name] = rhraceformat.id

    raceClass_ids = {}
    for rhraceclass in RHData.get_raceClasses():
        raceClass_ids[rhraceclass.name] = rhraceclass.id
    
    pilot_ids = {}
    for rhpilot in RHData.get_pilots():
        pilot_ids[rhpilot.callsign] = rhpilot.id

    for race_class_name, race_class in race_classes.items():
        raceClass_id = raceClass_ids.get(race_class_name, None)
        if not raceClass_id:
            class_data = {
                'name': race_class_name
            }
            if 'description' in race_class:
                class_data['description'] = race_class['description']
            if 'format' in race_class:
                raceFormat_name = race_class['format']
                if raceFormat_name in raceFormat_ids:
                    class_data['format_id'] = raceFormat_ids[raceFormat_name]
            rhraceclass = RHData.add_raceClass(class_data)
            raceClass_ids[race_class_name] = rhraceclass.id

    for callsign, pilot in pilots.items():
        pilot_id = pilot_ids.get(callsign, None)
        if not pilot_id:
            pilot_data = {
                'callsign': callsign,
                'name': pilot['name']
            }
            if 'url' in pilot:
                pilot_data['url'] = pilot['url']
            rhpilot = RHData.add_pilot(pilot_data)
            pilot_ids[callsign] = rhpilot.id

    rhheats = RHData.get_heats()
    h = 0
    for stage in stages:
        for heat in stage['heats']:
            if h < len(rhheats):
                rhheat = rhheats[h]
                heat_nodes = RHData.get_heatNodes_by_heat(rhheat.id)
                for seat_index in range(len(heat_nodes), len(heat['seats'])):
                    RHData.add_heatNode(rhheat.id, seat_index)
                for seat,callsign in enumerate(heat['seats']):
                    if callsign in pilot_ids:
                        heat_data = {'heat': rhheat.id, 'note': heat['name'], 'stage': stage['name'], 'node': seat, 'pilot': pilot_ids[callsign]}
                        if 'class' in heat:
                            heat_data['class'] = raceClass_ids[heat['class']]
                        RHData.alter_heat(heat_data)
            else:
                heat_data = {'note': heat['name'], 'stage': stage['name']}
                if 'class' in heat:
                    heat_data['class'] = raceClass_ids[heat['class']]
                heat_pilots = {}
                for seat,callsign in enumerate(heat['seats']):
                    if callsign in pilot_ids:
                        heat_pilots[seat] = pilot_ids[callsign]
                RHData.add_heat(init=heat_data, initPilots=heat_pilots)
            h += 1
    for i in range(len(rhheats)-1, h-1, -1):
        RHData.delete_heat(rhheats[i].id)

    rhserver['on_set_profile']({'profile': profile.id})
    rhserver['emit_pilot_data']()
    rhserver['emit_heat_data']()


def calculate_metrics(results, event_data):
    event_name = event_data['name']
    for pilot_result in results['pilots'].values():
        event_result = pilot_result['events'].get(event_name, {})
        for stage_idx, stage_result in event_result['stages'].items():
            stage_info = lookup_by_index_or_id(event_data['stages'], stage_idx)
            for heat_idx, heat_result in stage_result['heats'].items():
                if stage_info:
                    heat_info = lookup_by_index_or_id(stage_info['heats'], heat_idx)
                    race_class_name = heat_info['class']
                    heat_result['class'] = race_class_name
                    race_class = event_data['classes'].get(race_class_name, {})
                else:
                    race_class = {}
                if race_class:
                    race_format = event_data['formats'].get(race_class.get('format', ''))
                else:
                    race_format = {}
                for race_result in heat_result['rounds']:
                    race_metrics = calculate_race_metrics(race_result, race_format)
                    race_result['metrics'] = race_metrics
                heat_result['metrics'] = aggregate_metrics([r['metrics'] for r in heat_result['rounds']])
            stage_result['metrics'] = {}
            stage_metrics = stage_result['metrics']
            for race_class in event_data['classes']:
                stage_metrics[race_class] = aggregate_metrics([h['metrics'] for h in stage_result['heats'].values() if h['class'] == race_class])
        event_result['metrics'] = {}
        event_metrics = event_result['metrics']
        for race_class in event_data['classes']:
            event_metrics[race_class] = aggregate_metrics([s['metrics'][race_class] for s in event_result['stages'].values()])
    return results


def calculate_race_metrics(race, race_format):
    laps = race['laps']
    if race_format.get('start', 'first-pass') == 'start-line':
        start_time = 0
    else:
        start_time = laps[0]['timestamp'] if laps else None
        laps = laps[1:]
    lap_count = len(laps)
    race_time = laps[-1]['timestamp'] - start_time if lap_count else 0
    lap_times = [laps[i]['timestamp'] - (laps[i-1]['timestamp'] if i-1 >= 0 else start_time) for i in range(len(laps))]
    return {
        'lapCount': lap_count,
        'time': race_time,
        'lapTimes': lap_times,
        'fastest': np.min(lap_times),
        'mean': np.mean(lap_times),
        'stdDev': np.std(lap_times),
        'fastest3Consecutive': best_n_consecutive(lap_times, 3)
    }


def aggregate_metrics(metrics):
    lap_count = np.sum([r['lapCount'] for r in metrics])
    race_time = np.sum([r['time'] for r in metrics])
    lap_times = list(itertools.chain(*[r['lapTimes'] for r in metrics]))
    consec_totals = [np.sum(r['fastest3Consecutive']) for r in metrics]
    if consec_totals:
        idx = np.argmin(consec_totals)
        consecs = metrics[idx]['fastest3Consecutive']
    else:
        consecs = []
    return {
        'lapCount': lap_count,
        'time': race_time,
        'lapTimes': lap_times,
        'fastest': np.min(lap_times),
        'mean': np.mean(lap_times),
        'stdDev': np.std(lap_times),
        'fastest3Consecutive': consecs
    }


def best_n_consecutive(arr, n):
    consec_totals = [np.sum(arr[i:i+n]) for i in range(len(arr)+1-n)]
    if consec_totals:
        idx = np.argmin(consec_totals)
        return arr[idx:idx+n]
    else:
        return []


ID_PREFIX = 'id:'

def lookup_by_index_or_id(arr, key):
    if key.startswith(ID_PREFIX):
        entry_id = key.substring(len(ID_PREFIX))
        matching_entries = filter(lambda e: e['id'] == entry_id, arr)
        return matching_entries[0] if matching_entries else []
    else:
        return arr[int(key)]
