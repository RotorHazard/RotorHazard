'''JSON data exporter'''

import logging
logger = logging.getLogger(__name__)
import RHUtils
import json
from sqlalchemy.ext.declarative import DeclarativeMeta
from data_export import DataExporter

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

def assemble_all(RHData, PageCache, Language):
    payload = {}
    payload['Pilots'] = assemble_pilots(RHData, PageCache, Language)
    payload['Heats'] = assemble_heats(RHData, PageCache, Language)
    payload['Classes'] = assemble_classes(RHData, PageCache, Language)
    payload['Formats'] = assemble_formats(RHData, PageCache, Language)
    payload['Results'] = assemble_results(RHData, PageCache, Language)
    return payload

def assemble_pilots(RHData, PageCache, Language):
    pilots = RHData.get_pilots()
    payload = []
    for pilot in pilots:
        # payload.append(pilot)
        payload.append({
            'Callsign': pilot.callsign,
            'Name': pilot.name,
            'Team': pilot.team,
        })

    return payload

def assemble_heats(RHData, PageCache, Language):
    payload = {}
    for heat in RHData.get_heats():
        heat_id = heat.id
        note = heat.note

        if heat.class_id != RHUtils.CLASS_ID_NONE:
            race_class = RHData.get_raceClass(heat.class_id).name
        else:
            race_class = None

        heatnodes = RHData.get_heatNodes(filter_by={'heat_id': heat.id})
        pilots = {}
        for heatnode in heatnodes:
            if heatnode.pilot_id != RHUtils.PILOT_ID_NONE:
                pilots[heatnode.node_index] = RHData.get_pilot(heatnode.pilot_id).callsign
            else:
                pilots[heatnode.node_index] = None

        payload[heat_id] = {
            'Name': note,
            'Class': race_class,
            'Pilots': pilots,
        }

    return payload

def assemble_classes(RHData, PageCache, Language):
    race_classes = RHData.get_raceClasses()
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
            class_payload['Race Format'] = RHData.get_raceFormat(race_class.format_id).name

        payload.append(class_payload)

    return payload

def assemble_formats(RHData, PageCache, Language):
    timer_modes = [
        Language.__('Fixed Time'),
        Language.__('No Time Limit'),
    ]
    tones = [
        Language.__('None'),
        Language.__('One'),
        Language.__('Each Second')
    ]
    win_conditions = [  #pylint: disable=unused-variable
        Language.__('None'),
        Language.__('Most Laps in Fastest Time'),
        Language.__('First to X Laps'),
        Language.__('Fastest Lap'),
        Language.__('Fastest 3 Consecutive Laps'),
        Language.__('Most Laps Only'),
        Language.__('Most Laps Only with Overtime')
    ]
    start_behaviors = [
        Language.__('Hole Shot'),
        Language.__('First Lap'),
        Language.__('Staggered Start'),
    ]

    formats = RHData.get_raceFormats()
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

def assemble_results(RHData, PageCache, Language):
    payload = PageCache.get_cache()
    return payload

def assemble_complete(RHData, PageCache, Language):
    payload = {}
    payload['Pilot'] = assemble_pilots_complete(RHData, PageCache, Language)
    payload['Heat'] = assemble_heats_complete(RHData, PageCache, Language)
    payload['HeatNode'] = assemble_heatnodes_complete(RHData, PageCache, Language)
    payload['RaceClass'] = assemble_classes_complete(RHData, PageCache, Language)
    payload['RaceFormat'] = assemble_formats_complete(RHData, PageCache, Language)
    payload['SavedRaceMeta'] = assemble_racemeta_complete(RHData, PageCache, Language)
    payload['SavedPilotRace'] = assemble_pilotrace_complete(RHData, PageCache, Language)
    payload['SavedRaceLap'] = assemble_racelap_complete(RHData, PageCache, Language)
    payload['LapSplit'] = assemble_split_complete(RHData, PageCache, Language)
    payload['Profiles'] = assemble_profiles_complete(RHData, PageCache, Language)
    payload['GlobalSettings'] = assemble_settings_complete(RHData, PageCache, Language)
    return payload

def assemble_results_raw(RHData, PageCache, Language):
    payload = PageCache.get_cache()
    return payload

def assemble_pilots_complete(RHData, PageCache, Language):
    payload = RHData.get_pilots()
    return payload

def assemble_heats_complete(RHData, PageCache, Language):
    payload = RHData.get_heats()
    return payload

def assemble_heatnodes_complete(RHData, PageCache, Language):
    payload = RHData.get_heatNodes()
    return payload

def assemble_classes_complete(RHData, PageCache, Language):
    payload = RHData.get_raceClasses()
    return payload

def assemble_formats_complete(RHData, PageCache, Language):
    payload = RHData.get_raceFormats()
    return payload

def assemble_split_complete(RHData, PageCache, Language):
    payload = RHData.get_lapSplits()
    return payload

def assemble_racemeta_complete(RHData, PageCache, Language):
    payload = RHData.get_savedRaceMetas()
    return payload

def assemble_pilotrace_complete(RHData, PageCache, Language):
    payload = RHData.get_savedPilotRaces()
    return payload

def assemble_racelap_complete(RHData, PageCache, Language):
    payload = RHData.get_savedRaceLaps()
    return payload

def assemble_profiles_complete(RHData, PageCache, Language):
    payload = RHData.get_profiles()
    return payload

def assemble_settings_complete(RHData, PageCache, Language):
    payload = RHData.get_options()
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

def discover(*args, **kwargs):
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
