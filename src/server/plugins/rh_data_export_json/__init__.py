'''JSON data exporter'''

import logging
import RHUtils
import json
from sqlalchemy.ext.declarative import DeclarativeMeta
from data_export import DataExporter

logger = logging.getLogger(__name__)

def registerHandlers(args):
    if 'registerFn' in args:
        for exporter in discover():
            args['registerFn'](exporter)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('Export_Initialize', 'Export_register_JSON', registerHandlers, {}, 75)

def write_json(data):
    payload = json.dumps(data, indent='\t', cls=AlchemyEncoder)

    return {
        'data': payload,
        'encoding': 'application/json',
        'ext': 'json'
    }

def assemble_all(RHAPI):
    payload = {}
    payload['Pilots'] = assemble_pilots(RHAPI)
    payload['Heats'] = assemble_heats(RHAPI)
    payload['Classes'] = assemble_classes(RHAPI)
    payload['Formats'] = assemble_formats(RHAPI)
    payload['Results'] = assemble_results(RHAPI)
    return payload

def assemble_pilots(RHAPI):
    pilots = RHAPI.db.pilots
    payload = []
    for pilot in pilots:
        # payload.append(pilot)
        payload.append({
            'Callsign': pilot.callsign,
            'Name': pilot.name,
            'Team': pilot.team,
        })

    return payload

def assemble_heats(RHAPI):
    payload = {}
    for heat in RHAPI.db.heats:
        heat_id = heat.id
        displayname = heat.display_name()

        if heat.class_id != RHUtils.CLASS_ID_NONE:
            race_class_name = RHAPI.db.raceclass_by_id(heat.class_id).name
        else:
            race_class_name = None

        heatnodes = RHAPI.db.slots_by_heat(heat.id)
        pilots = {}
        for heatnode in heatnodes:
            if heatnode.pilot_id != RHUtils.PILOT_ID_NONE:
                pilots[heatnode.node_index] = RHAPI.db.pilot_by_id(heatnode.pilot_id).callsign
            else:
                pilots[heatnode.node_index] = None

        payload[heat_id] = {
            'Name': displayname,
            'Class': race_class_name,
            'Pilots': pilots,
        }

    return payload

def assemble_classes(RHAPI):
    race_classes = RHAPI.db.raceclasses
    payload = []
    for race_class in race_classes:
        # payload.append(race_class)
        # expand format id to name
        class_payload = {
            'Name': race_class.name,
            'Description': race_class.description,
            'Race Format': None
        }

        if race_class.format_id:
            class_payload['Race Format'] = RHAPI.db.raceformat_by_id(race_class.format_id).name

        payload.append(class_payload)

    return payload

def assemble_formats(RHAPI):
    timer_modes = [
        RHAPI.__('Fixed Time'),
        RHAPI.__('No Time Limit'),
    ]
    tones = [
        RHAPI.__('None'),
        RHAPI.__('One'),
        RHAPI.__('Each Second')
    ]
    win_conditions = [  #pylint: disable=unused-variable
        RHAPI.__('None'),
        RHAPI.__('Most Laps in Fastest Time'),
        RHAPI.__('First to X Laps'),
        RHAPI.__('Fastest Lap'),
        RHAPI.__('Fastest Consecutive Laps'),
        RHAPI.__('Most Laps Only'),
        RHAPI.__('Most Laps Only with Overtime')
    ]
    start_behaviors = [
        RHAPI.__('Hole Shot'),
        RHAPI.__('First Lap'),
        RHAPI.__('Staggered Start'),
    ]

    formats = RHAPI.db.raceformats
    payload = []
    for race_format in formats:
        # payload.append(race_format)

        payload.append({
            'Name': race_format.name,
            'Mode': timer_modes[race_format.race_mode],
            'Duration (seconds)': race_format.race_time_sec,
            'Minimum Start Delay': race_format.start_delay_min_ms,
            'Maximum Start Delay': race_format.start_delay_max_ms,
            'Staging Tones': tones[race_format.staging_tones],
            'Win Condition': race_format.win_condition,
            'Laps to Win': race_format.number_laps_win,
            'Team Racing': race_format.team_racing_mode,
            'First Crossing': start_behaviors[race_format.start_behavior],
        })

    return payload

def assemble_results(RHAPI):
    payload = RHAPI.eventresults.results
    return payload

def assemble_complete(RHAPI):
    payload = {}
    payload['Pilot'] = assemble_pilots_complete(RHAPI)
    payload['Heat'] = assemble_heats_complete(RHAPI)
    payload['HeatNode'] = assemble_heatnodes_complete(RHAPI)
    payload['RaceClass'] = assemble_classes_complete(RHAPI)
    payload['RaceFormat'] = assemble_formats_complete(RHAPI)
    payload['SavedRaceMeta'] = assemble_racemeta_complete(RHAPI)
    payload['SavedPilotRace'] = assemble_pilotrace_complete(RHAPI)
    payload['SavedRaceLap'] = assemble_racelap_complete(RHAPI)
    payload['Profiles'] = assemble_profiles_complete(RHAPI)
    payload['GlobalSettings'] = assemble_settings_complete(RHAPI)
    return payload

def assemble_results_raw(RHAPI):
    payload = RHAPI.eventresults.results
    return payload

def assemble_pilots_complete(RHAPI):
    payload = RHAPI.db.pilots
    return payload

def assemble_heats_complete(RHAPI):
    payload = RHAPI.db.heats
    return payload

def assemble_heatnodes_complete(RHAPI):
    payload = RHAPI.db.slots
    return payload

def assemble_classes_complete(RHAPI):
    payload = RHAPI.db.raceclasses
    return payload

def assemble_formats_complete(RHAPI):
    payload = RHAPI.db.raceformats
    return payload

def assemble_racemeta_complete(RHAPI):
    payload = RHAPI.db.races
    return payload

def assemble_pilotrace_complete(RHAPI):
    payload = RHAPI.db.pilotruns
    return payload

def assemble_racelap_complete(RHAPI):
    payload = RHAPI.db.laps
    return payload

def assemble_profiles_complete(RHAPI):
    payload = RHAPI.db.frequencysets
    return payload

def assemble_settings_complete(RHAPI):
    payload = RHAPI.db.options
    return payload

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
                            fields[field] = json.loads(data)
                        elif field == "enter_ats" or field == "exit_ats":
                            fields[field] = json.loads(data)
                        else:
                            fields[field] = data
                    except TypeError:
                        fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)

def discover(*_args, **_kwargs):
    # returns array of exporters with default arguments
    return [
        DataExporter(
            'json_pilots',
            'JSON (Friendly) / Pilots',
            write_json,
            assemble_pilots
        ),
        DataExporter(
            'json_heats',
            'JSON (Friendly) / Heats',
            write_json,
            assemble_heats
        ),
        DataExporter(
            'json_classes',
            'JSON (Friendly) / Classes',
            write_json,
            assemble_classes
        ),
        DataExporter(
            'json_formats',
            'JSON (Friendly) / Formats',
            write_json,
            assemble_formats
        ),
        DataExporter(
            'json_results',
            'JSON (Friendly) / Results',
            write_json,
            assemble_results
        ),
        DataExporter(
            'json_all',
            'JSON (Friendly) / All',
            write_json,
            assemble_all
        ),
        DataExporter(
            'json_complete_all',
            'JSON (Complete) / All',
            write_json,
            assemble_complete
        ),
        DataExporter(
            'json_complete_results',
            'JSON (Complete) / Results',
            write_json,
            assemble_results_raw
        )
    ]
