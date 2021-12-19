import json
from flask import request
from flask.blueprints import Blueprint
from .RHUtils import VTX_TABLE

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
        event_name = RHData.get_option('eventName', '')
        msgs = []
        for race in RHData.get_savedRaceMetas():
            race_id = race.id
            round_id = race.round_id
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
                    msg = {'event': event_name, 'stage': stage_id, 'round': round_id, 'heat': heat_id, 'pilot': pilot.callsign, 'laps': laps}
                    msgs.append(msg)
        return '\n'.join([json.dumps(msg) for msg in msgs])

    @APP.route('/raceEvent', methods=['GET'])
    def race_event_get():
        event_name = RHData.get_option('eventName', "")
        event_desc = RHData.get_option('eventDescription', "")
        event_url = RHData.get_option('eventURL', "")
        pilots = {}
        pilots_by_id = {}
        for pilot in RHData.get_pilots():
            pilots[pilot.callsign] = {'name': pilot.name}
            pilots_by_id[pilot.id] = pilot
        race_formats_by_id = {0: None}
        for race_format in RHData.get_raceFormats():
            race_formats_by_id[race_format.id] = race_format.name
        race_classes = {"Unclassified": {'description': "Default class"}}
        race_classes_by_id = {0: "Unclassified"}
        for race_class in RHData.get_raceClasses():
            race_classes[race_class.name] = {
                'description': race_class.description,
                'format': race_formats_by_id[race_class.format_id]
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

        stages = []
        prev_stage_name = None
        for heat_idx, heat_data in enumerate(RHData.get_heats()):
            heat_seats = [None] * len(seats)
            for heat_node in RHData.get_heatNodes_by_heat(heat_data.id):
                if heat_node.pilot_id in pilots_by_id:
                    heat_seats[heat_node.node_index] = pilots_by_id[heat_node.pilot_id].callsign
            race_name = heat_data.note if heat_data.note else 'Heat '+str(heat_idx+1)
            race = {
                'id': str(heat_data.id),
                'name': race_name,
                'class': race_classes_by_id[heat_data.class_id],
                'seats': heat_seats
            }
            stage_name = heat_data.stage.name
            if stage_name != prev_stage_name:
                races = []
                stage = {'id': str(heat_data.stage_id), 'name': stage_name, 'races': races}
                stages.append(stage)
                prev_stage_name = stage_name
            races.append(race)
        data = {
            'name': event_name,
            'description': event_desc,
            'url': event_url,
            'pilots': pilots,
            'classes': race_classes,
            'seats': seats,
            'stages': stages
        }
        return data

    @APP.route('/raceEvent', methods=['PUT'])
    def race_event_post():
        data = request.get_json()
        import_event(data, rhserver)
        return '', 204

    @APP.route('/trackLayout', methods=['GET'])
    def track_layout_get():
        track = RHData.get_option('trackLayout', None)
        if track:
            track = json.loads(track)
        if not track or not track['layout']:
            track = {
                'crs': 'Local grid',
                'units': 'm',
                'layout': [{'name': 'Start/finish', 'type': 'Arch gate', 'location': [0,0]}],
                'types': ["Arch gate", "Square gate", "Flag"]
            }
            RHData.set_option('trackLayout', json.dumps(track))
        return track

    @APP.route('/trackLayout', methods=['PUT'])
    def track_layout_post():
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
        return '\n'.join([json.dumps(msg) for msg in msgs])

    @APP.route('/vtxTable')
    def vtx_table():
        return VTX_TABLE

    return APP


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
        for race in stage['races']:
            if h < len(rhheats):
                rhheat = rhheats[h]
                heat_nodes = RHData.get_heatNodes_by_heat(rhheat.id)
                for seat_index in range(len(heat_nodes), len(race['seats'])):
                    RHData.add_heatNode(rhheat.id, seat_index)
                for seat,callsign in enumerate(race['seats']):
                    if callsign in pilot_ids:
                        heat_data = {'heat': rhheat.id, 'note': race['name'], 'stage': stage['name'], 'node': seat, 'pilot': pilot_ids[callsign]}
                        if 'class' in race:
                            heat_data['class'] = raceClass_ids[race['class']]
                        RHData.alter_heat(heat_data)
            else:
                heat_data = {'note': race['name'], 'stage': stage['name']}
                if 'class' in race:
                    heat_data['class'] = raceClass_ids[race['class']]
                heat_pilots = {}
                for seat,callsign in enumerate(race['seats']):
                    if callsign in pilot_ids:
                        heat_pilots[seat] = pilot_ids[callsign]
                RHData.add_heat(init=heat_data, initPilots=heat_pilots)
            h += 1
    for i in range(len(rhheats)-1, h-1, -1):
        RHData.delete_heat(rhheats[i].id)

    rhserver['on_set_profile']({'profile': profile.id})
    rhserver['emit_pilot_data']()
    rhserver['emit_heat_data']()
