'''JSON data exporter'''

import logging
logger = logging.getLogger(__name__)
from Language import __
import RHUtils
import json
from sqlalchemy.ext.declarative import DeclarativeMeta
from data_export import DataExporter


def write_json(data):
    payload = json.dumps(data, indent='\t', cls=AlchemyEncoder)

    return {
        'data': payload,
        'encoding': 'application/json',
        'ext': 'json'
    }

def assemble_all(Database, PageCache):
    payload = {}
    payload['Pilots'] = assemble_pilots(Database, PageCache)
    payload['Heats'] = assemble_heats(Database, PageCache)
    payload['Classes'] = assemble_classes(Database, PageCache)
    payload['Formats'] = assemble_formats(Database, PageCache)
    payload['Results'] = assemble_results(Database, PageCache)
    return payload

def assemble_pilots(Database, PageCache):
    pilots = Database.Pilot.query.all()
    payload = []
    for pilot in pilots:
        # payload.append(pilot)
        payload.append({
            'Callsign': pilot.callsign,
            'Name': pilot.name,
            'Team': pilot.team,
        })

    return payload

def assemble_heats(Database, PageCache):
    payload = {}
    for heat in Database.Heat.query.all():
        heat_id = heat.id
        note = heat.note

        if heat.class_id != RHUtils.CLASS_ID_NONE:
            race_class = Database.RaceClass.query.get(heat.class_id).name
        else:
            race_class = None

        heatnodes = Database.HeatNode.query.filter_by(heat_id=heat.id).all()
        pilots = {}
        for heatnode in heatnodes:
            if heatnode.pilot_id != RHUtils.PILOT_ID_NONE:
                pilots[heatnode.node_index] = Database.Pilot.query.get(heatnode.pilot_id).callsign
            else:
                pilots[heatnode.node_index] = None

        payload[heat_id] = {
            'Name': note,
            'Class': race_class,
            'Pilots': pilots,
        }

    return payload

def assemble_classes(Database, PageCache):
    race_classes = Database.RaceClass.query.all()
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
            class_payload['Race Format'] = Database.RaceFormat.query.get(race_class.format_id).name

        payload.append(class_payload)

    return payload

def assemble_formats(Database, PageCache):
    timer_modes = [
        __('Fixed Time'),
        __('No Time Limit'),
    ]
    tones = [
        __('None'),
        __('One'),
        __('Each Second')
    ]
    win_conditions = [
        __('None'),
        __('Most Laps in Fastest Time'),
        __('First to X Laps'),
        __('Fastest Lap'),
        __('Fastest 3 Consecutive Laps'),
        __('Most Laps Only'),
        __('Most Laps Only with Overtime')
    ]
    start_behaviors = [
        __('Hole Shot'),
        __('First Lap'),
        __('Staggered Start'),
    ]

    formats = Database.RaceFormat.query.all()
    payload = []
    for race_format in formats:
        # payload.append(race_format)

        payload.append({
            'Name': race_format.name,
            'Mode': timer_modes[race_format.race_mode],
            'Duration (seconds)': race_format.race_time_sec,
            'Minimum Start Delay': race_format.start_delay_min,
            'Maximum Start Delay': race_format.start_delay_max,
            'Staging Tones': tones[race_format.staging_tones],
            'Win Condition': race_format.win_condition,
            'Laps to Win': race_format.number_laps_win,
            'Team Racing': race_format.team_racing_mode,
            'First Crossing': start_behaviors[race_format.start_behavior],
        })

    return payload

def assemble_results(Database, PageCache):
    # TODO: Make results friendly
    payload = PageCache.get_cache()
    return payload

def assemble_complete(Database, PageCache):
    payload = {}
    payload['Pilot'] = assemble_pilots_complete(Database, PageCache)
    payload['Heat'] = assemble_heats_complete(Database, PageCache)
    payload['HeatNode'] = assemble_heatnodes_complete(Database, PageCache)
    payload['RaceClass'] = assemble_classes_complete(Database, PageCache)
    payload['RaceFormat'] = assemble_formats_complete(Database, PageCache)
    payload['SavedRaceMeta'] = assemble_racemeta_complete(Database, PageCache)
    payload['SavedPilotRace'] = assemble_pilotrace_complete(Database, PageCache)
    payload['SavedRaceLap'] = assemble_racelap_complete(Database, PageCache)
    payload['LapSplit'] = assemble_split_complete(Database, PageCache)
    payload['Profiles'] = assemble_profiles_complete(Database, PageCache)
    payload['GlobalSettings'] = assemble_settings_complete(Database, PageCache)
    return payload

def assemble_results_raw(Database, PageCache):
    payload = PageCache.get_cache()
    return payload

def assemble_pilots_complete(Database, PageCache):
    payload = Database.Pilot.query.all()
    return payload

def assemble_heats_complete(Database, PageCache):
    payload = Database.Heat.query.all()
    return payload

def assemble_heatnodes_complete(Database, PageCache):
    payload = Database.HeatNode.query.all()
    return payload

def assemble_classes_complete(Database, PageCache):
    payload = Database.RaceClass.query.all()
    return payload

def assemble_formats_complete(Database, PageCache):
    payload = Database.RaceFormat.query.all()
    return payload

def assemble_split_complete(Database, PageCache):
    payload = Database.LapSplit.query.all()
    return payload

def assemble_racemeta_complete(Database, PageCache):
    payload = Database.SavedRaceMeta.query.all()
    return payload

def assemble_pilotrace_complete(Database, PageCache):
    payload = Database.SavedPilotRace.query.all()
    return payload

def assemble_racelap_complete(Database, PageCache):
    payload = Database.SavedRaceLap.query.all()
    return payload

def assemble_profiles_complete(Database, PageCache):
    payload = Database.Profiles.query.all()
    return payload

def assemble_settings_complete(Database, PageCache):
    payload = Database.GlobalSettings.query.all()
    return payload

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
