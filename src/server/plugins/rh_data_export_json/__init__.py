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
        kwargs['Events'].on('Export_Initialize', 'Export_register_JSON', registerHandlers, {}, 75, True)

def write_json(data):
    payload = json.dumps(data, indent='\t', cls=AlchemyEncoder)

    return {
        'data': payload,
        'encoding': 'application/json',
        'ext': 'json'
    }

def assemble_all(RaceContext):
    payload = {}
    payload['Pilots'] = assemble_pilots(RaceContext)
    payload['Heats'] = assemble_heats(RaceContext)
    payload['Classes'] = assemble_classes(RaceContext)
    payload['Formats'] = assemble_formats(RaceContext)
    payload['Results'] = assemble_results(RaceContext)
    return payload

def assemble_pilots(RaceContext):
    pilots = RaceContext.rhdata.get_pilots()
    payload = []
    for pilot in pilots:
        # payload.append(pilot)
        payload.append({
            'Callsign': pilot.callsign,
            'Name': pilot.name,
            'Team': pilot.team,
        })

    return payload

def assemble_heats(RaceContext):
    payload = {}
    for heat in RaceContext.rhdata.get_heats():
        heat_id = heat.id
        displayname = heat.displayname()

        if heat.class_id != RHUtils.CLASS_ID_NONE:
            race_class = RaceContext.rhdata.get_raceClass(heat.class_id).name
        else:
            race_class = None

        heatnodes = RaceContext.rhdata.get_heatNodes_by_heat(heat.id)
        pilots = {}
        for heatnode in heatnodes:
            if heatnode.pilot_id != RHUtils.PILOT_ID_NONE:
                pilots[heatnode.node_index] = RaceContext.rhdata.get_pilot(heatnode.pilot_id).callsign
            else:
                pilots[heatnode.node_index] = None

        payload[heat_id] = {
            'Name': displayname,
            'Class': race_class,
            'Pilots': pilots,
        }

    return payload

def assemble_classes(RaceContext):
    race_classes = RaceContext.rhdata.get_raceClasses()
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
            class_payload['Race Format'] = RaceContext.rhdata.get_raceFormat(race_class.format_id).name

        payload.append(class_payload)

    return payload

def assemble_formats(RaceContext):
    timer_modes = [
        RaceContext.language.__('Fixed Time'),
        RaceContext.language.__('No Time Limit'),
    ]
    tones = [
        RaceContext.language.__('None'),
        RaceContext.language.__('One'),
        RaceContext.language.__('Each Second')
    ]
    win_conditions = [  #pylint: disable=unused-variable
        RaceContext.language.__('None'),
        RaceContext.language.__('Most Laps in Fastest Time'),
        RaceContext.language.__('First to X Laps'),
        RaceContext.language.__('Fastest Lap'),
        RaceContext.language.__('Fastest 3 Consecutive Laps'),
        RaceContext.language.__('Most Laps Only'),
        RaceContext.language.__('Most Laps Only with Overtime')
    ]
    start_behaviors = [
        RaceContext.language.__('Hole Shot'),
        RaceContext.language.__('First Lap'),
        RaceContext.language.__('Staggered Start'),
    ]

    formats = RaceContext.rhdata.get_raceFormats()
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

def assemble_results(RaceContext):
    payload = RaceContext.pagecache.get_cache()
    return payload

def assemble_complete(RaceContext):
    payload = {}
    payload['Pilot'] = assemble_pilots_complete(RaceContext)
    payload['Heat'] = assemble_heats_complete(RaceContext)
    payload['HeatNode'] = assemble_heatnodes_complete(RaceContext)
    payload['RaceClass'] = assemble_classes_complete(RaceContext)
    payload['RaceFormat'] = assemble_formats_complete(RaceContext)
    payload['SavedRaceMeta'] = assemble_racemeta_complete(RaceContext)
    payload['SavedPilotRace'] = assemble_pilotrace_complete(RaceContext)
    payload['SavedRaceLap'] = assemble_racelap_complete(RaceContext)
    payload['LapSplit'] = assemble_split_complete(RaceContext)
    payload['Profiles'] = assemble_profiles_complete(RaceContext)
    payload['GlobalSettings'] = assemble_settings_complete(RaceContext)
    return payload

def assemble_results_raw(RaceContext):
    payload = RaceContext.pagecache.get_cache()
    return payload

def assemble_pilots_complete(RaceContext):
    payload = RaceContext.rhdata.get_pilots()
    return payload

def assemble_heats_complete(RaceContext):
    payload = RaceContext.rhdata.get_heats()
    return payload

def assemble_heatnodes_complete(RaceContext):
    payload = RaceContext.rhdata.get_heatNodes()
    return payload

def assemble_classes_complete(RaceContext):
    payload = RaceContext.rhdata.get_raceClasses()
    return payload

def assemble_formats_complete(RaceContext):
    payload = RaceContext.rhdata.get_raceFormats()
    return payload

def assemble_split_complete(RaceContext):
    payload = RaceContext.rhdata.get_lapSplits()
    return payload

def assemble_racemeta_complete(RaceContext):
    payload = RaceContext.rhdata.get_savedRaceMetas()
    return payload

def assemble_pilotrace_complete(RaceContext):
    payload = RaceContext.rhdata.get_savedPilotRaces()
    return payload

def assemble_racelap_complete(RaceContext):
    payload = RaceContext.rhdata.get_savedRaceLaps()
    return payload

def assemble_profiles_complete(RaceContext):
    payload = RaceContext.rhdata.get_profiles()
    return payload

def assemble_settings_complete(RaceContext):
    payload = RaceContext.rhdata.get_options()
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
