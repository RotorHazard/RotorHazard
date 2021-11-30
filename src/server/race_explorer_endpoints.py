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
        eventName = RHData.get_option('eventName', '')
        msgs = []
        for race in RHData.get_savedRaceMetas():
            round_id = race.round_id
            heat_id = race.heat_id
            pilotraces = RHData.get_savedPilotRaces_by_savedRaceMeta(race.id)
            for pilotrace in pilotraces:
                pilot = RHData.get_pilot(pilotrace.pilot_id)
                pilotlaps = RHData.get_savedRaceLaps_by_savedPilotRace(pilotrace.id)
                laps = [{'lap': i, 'timestamp': pilotlap.lap_time_stamp, 'timer': TIMER_ID} for i,pilotlap in enumerate(pilotlaps)]
                msg = {'event': eventName, 'round': round_id, 'heat': heat_id, 'pilot': pilot.callsign, 'laps': laps}
                msgs.append(msg)
        return '\n'.join([json.dumps(msg) for msg in msgs])

    @APP.route('/raceEvent')
    def race_event():
        data = {}
        for pilot in RHData.get_pilots():
            data[pilot.callsign] = {}
        return data

    @APP.route('/trackLayout', methods=['GET'])
    def track_layout_get():
        track = RHData.get_option('trackLayout', None)
        if track:
            track = json.loads(track)
        else:
            track = {
                'crs': 'Local grid',
                'units': 'm',
                'layout': [{'name': 'Start/finish', 'type': 'Arch gate', 'location': [0,0]}]
            }
        return track

    @APP.route('/trackLayout', methods=['POST'])
    def track_layout_post():
        data = request.get_json()
        RHData.set_option('trackLayout', json.dumps(data))
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

