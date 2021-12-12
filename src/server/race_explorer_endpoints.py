import json
from flask import request
from flask.blueprints import Blueprint
from .RHUtils import VTX_TABLE

def createBlueprint(rhconfig, TIMER_ID, INTERFACE, RHData):
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
                    msg = {'event': event_name, 'round': round_id, 'heat': heat_id, 'pilot': pilot.callsign, 'laps': laps}
                    msgs.append(msg)
        return '\n'.join([json.dumps(msg) for msg in msgs])

    @APP.route('/raceEvent', methods=['GET'])
    def race_event_get():
        event_name = RHData.get_option('eventName')
        event_desc = RHData.get_option('eventDescription')
        event_url = RHData.get_option('eventURL')
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
            stage_name = 'Mains' if heat_data.note and heat_data.note.endswith(' Main') else 'Qualifying'
            race_name = heat_data.note if heat_data.note else 'Heat '+str(heat_idx+1)
            race = {
                'name': race_name,
                'class': race_classes_by_id[heat_data.class_id],
                'seats': heat_seats
            }
            if stage_name != prev_stage_name:
                races = []
                stage = {'name': stage_name, 'races': races}
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

    @APP.route('/raceEvent', methods=['POST'])
    def race_event_post():
        data = request.get_json()
        RHData.set_option('eventName', data['name'])
        RHData.set_option('eventDescription', data['description'])
        RHData.set_option('eventURL', data['url'])
        return '', 204

    @APP.route('/trackLayout', methods=['GET'])
    def track_layout_get():
        track = RHData.get_option('trackLayout', None)
        if track:
            track = json.loads(track)
        else:
            track = {
                'crs': 'Local grid',
                'units': 'm',
                'layout': [{'name': 'Start/finish', 'type': 'Arch gate', 'location': [0,0]}],
                'types': ["Arch gate", "Square gate", "Flag"]
            }
            RHData.set_option('trackLayout', json.dumps(track))
        return track

    @APP.route('/trackLayout', methods=['POST'])
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

    @APP.route('/timerMapping', methods=['POST'])
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

