'''JSON data exporter'''

import logging
import RHUtils
import json
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import inspect
from eventmanager import Evt
from data_export import DataExporter

logger = logging.getLogger(__name__)

def write_json(data):
    payload = json.dumps(data, indent='\t', cls=AlchemyEncoder)

    return {
        'data': payload,
        'encoding': 'application/json',
        'ext': 'json'
    }

def assemble_all(rhapi):
    payload = {}
    payload['Pilots'] = assemble_pilots(rhapi)
    payload['Heats'] = assemble_heats(rhapi)
    payload['Classes'] = assemble_classes(rhapi)
    payload['Formats'] = assemble_formats(rhapi)
    payload['Results'] = assemble_results(rhapi)
    return payload

def assemble_pilots(rhapi):
    pilots = rhapi.db.pilots
    payload = []
    for pilot in pilots:
        # payload.append(pilot)
        payload.append({
            'Callsign': pilot.callsign,
            'Name': pilot.name,
            'Team': pilot.team,
        })

    return payload

def assemble_heats(rhapi):
    payload = {}
    for heat in rhapi.db.heats:
        heat_id = heat.id
        displayname = heat.display_name

        if heat.class_id != RHUtils.CLASS_ID_NONE:
            race_class_name = rhapi.db.raceclass_by_id(heat.class_id).name
        else:
            race_class_name = None

        heatnodes = rhapi.db.slots_by_heat(heat.id)
        pilots = {}
        for heatnode in heatnodes:
            if heatnode.pilot_id != RHUtils.PILOT_ID_NONE:
                pilots[heatnode.node_index] = rhapi.db.pilot_by_id(heatnode.pilot_id).callsign
            else:
                pilots[heatnode.node_index] = None

        payload[heat_id] = {
            'Name': displayname,
            'Class': race_class_name,
            'Pilots': pilots,
        }

    return payload

def assemble_classes(rhapi):
    race_classes = rhapi.db.raceclasses
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
            class_payload['Race Format'] = rhapi.db.raceformat_by_id(race_class.format_id).name

        payload.append(class_payload)

    return payload

def assemble_formats(rhapi):
    timer_modes = [
        rhapi.__('Fixed Time'),
        rhapi.__('No Time Limit'),
    ]
    tones = [
        rhapi.__('None'),
        rhapi.__('One'),
        rhapi.__('Each Second')
    ]
    win_conditions = [  #pylint: disable=unused-variable
        rhapi.__('None'),
        rhapi.__('Most Laps in Fastest Time'),
        rhapi.__('First to X Laps'),
        rhapi.__('Fastest Lap'),
        rhapi.__('Fastest Consecutive Laps'),
        rhapi.__('Most Laps Only'),
        rhapi.__('Most Laps Only with Overtime')
    ]
    start_behaviors = [
        rhapi.__('Hole Shot'),
        rhapi.__('First Lap'),
        rhapi.__('Staggered Start'),
    ]

    formats = rhapi.db.raceformats
    payload = []
    for race_format in formats:
        # payload.append(race_format)

        payload.append({
            'Name': race_format.name,
            'Mode': timer_modes[race_format.unlimited_time],
            'Duration (seconds)': race_format.race_time_sec,
            'Minimum Start Delay': race_format.start_delay_min_ms,
            'Maximum Start Delay': race_format.start_delay_max_ms,
            'Staging Tones': tones[race_format.staging_delay_tones],
            'Win Condition': race_format.win_condition,
            'Laps to Win': race_format.number_laps_win,
            'Team Racing': race_format.team_racing_mode,
            'First Crossing': start_behaviors[race_format.start_behavior],
        })

    return payload

def assemble_results(rhapi):
    payload = rhapi.eventresults.results
    return payload

def assemble_complete(rhapi):
    payload = {}
    payload['Pilot'] = assemble_pilots_complete(rhapi)
    payload['Heat'] = assemble_heats_complete(rhapi)
    payload['HeatNode'] = assemble_heatnodes_complete(rhapi)
    payload['RaceClass'] = assemble_classes_complete(rhapi)
    payload['RaceFormat'] = assemble_formats_complete(rhapi)
    payload['SavedRaceMeta'] = assemble_racemeta_complete(rhapi)
    payload['SavedPilotRace'] = assemble_pilotrace_complete(rhapi)
    payload['SavedRaceLap'] = assemble_racelap_complete(rhapi)
    payload['Profiles'] = assemble_profiles_complete(rhapi)
    payload['GlobalSettings'] = assemble_settings_complete(rhapi)
    return payload

def assemble_results_raw(rhapi):
    payload = rhapi.eventresults.results
    return payload

def assemble_pilots_complete(rhapi):
    payload = rhapi.db.pilots
    return payload

def assemble_heats_complete(rhapi):
    payload = rhapi.db.heats
    return payload

def assemble_heatnodes_complete(rhapi):
    payload = rhapi.db.slots
    return payload

def assemble_classes_complete(rhapi):
    payload = rhapi.db.raceclasses
    return payload

def assemble_formats_complete(rhapi):
    payload = rhapi.db.raceformats
    return payload

def assemble_racemeta_complete(rhapi):
    payload = rhapi.db.races
    return payload

def assemble_pilotrace_complete(rhapi):
    payload = rhapi.db.pilotruns
    return payload

def assemble_racelap_complete(rhapi):
    payload = rhapi.db.laps
    return payload

def assemble_profiles_complete(rhapi):
    payload = rhapi.db.frequencysets
    return payload

def assemble_settings_complete(rhapi):
    payload = rhapi.db.options
    return payload

class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):  #pylint: disable=arguments-differ
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            mapped_instance = inspect(obj)
            fields = {}
            for field in mapped_instance.attrs.keys():
                data = obj.__getattribute__(field)
                if field != 'query' \
                    and field != 'query_class':
                    try:
                        json.dumps(data) # this will fail on non-encodable values, like other classes
                        if field == 'frequencies':
                            fields[field] = json.loads(data)
                        elif field == 'enter_ats' or field == 'exit_ats':
                            fields[field] = json.loads(data)
                        else:
                            fields[field] = data
                    except TypeError:
                        fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)

def register_handlers(args):
    for exporter in [
        DataExporter(
            'json_pilots',
            "JSON (Friendly) / Pilots",
            write_json,
            assemble_pilots
        ),
        DataExporter(
            'json_heats',
            "JSON (Friendly) / Heats",
            write_json,
            assemble_heats
        ),
        DataExporter(
            'json_classes',
            "JSON (Friendly) / Classes",
            write_json,
            assemble_classes
        ),
        DataExporter(
            'json_formats',
            "JSON (Friendly) / Formats",
            write_json,
            assemble_formats
        ),
        DataExporter(
            'json_results',
            "JSON (Friendly) / Results",
            write_json,
            assemble_results
        ),
        DataExporter(
            'json_all',
            "JSON (Friendly) / All",
            write_json,
            assemble_all
        ),
        DataExporter(
            'json_complete_all',
            "JSON (Complete) / All",
            write_json,
            assemble_complete
        ),
        DataExporter(
            'json_complete_results',
            "JSON (Complete) / Results",
            write_json,
            assemble_results_raw
        )
    ]:
        args['register_fn'](exporter)

def initialize(**kwargs):
    kwargs['events'].on(Evt.DATA_EXPORT_INITIALIZE, 'Export_register_JSON', register_handlers, {}, 75)

