'''JSON data exporter'''

import logging
logger = logging.getLogger(__name__)
from Language import __
import RHUtils
import json
from sqlalchemy.ext.declarative import DeclarativeMeta

def export_as_json(Database, PageCache, args):
    if 'fn' in args:
        payload = json.dumps(args['fn'](Database, PageCache), indent='\t', cls=AlchemyEncoder)

        return {
            'data': payload,
            'encoding': 'application/json',
            'ext': 'json'
        }
    else:
        return False

def export_all(Database, PageCache):
    payload = {}
    payload['Pilots'] = export_pilots(Database, PageCache)
    payload['Heats'] = export_heats(Database, PageCache)
    payload['Classes'] = export_classes(Database, PageCache)
    payload['Formats'] = export_formats(Database, PageCache)
    payload['Results'] = export_results(Database, PageCache)
    return payload

def export_pilots(Database, PageCache):
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

def export_heats(Database, PageCache):
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

def export_classes(Database, PageCache):
    race_classes = Database.RaceClass.query.all()
    payload = []
    for race_class in race_classes:
        # payload.append(race_class)
        # expand format id to name
        payload.append({
            'Name': race_class.name,
            'Description': race_class.description,
            'Race Format': Database.RaceFormat.query.get(race_class.format_id).name
        })

    return payload

def export_formats(Database, PageCache):
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

def export_results(Database, PageCache):
    payload = PageCache.data
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
        {
            'id': 'json_pilots',
            'name': 'JSON (Friendly) / Pilots',
            'handlerFn': export_as_json,
            'args': {
                'fn': export_pilots,
            },
        },
        {
            'id': 'json_heats',
            'name': 'JSON (Friendly) / Heats',
            'handlerFn': export_as_json,
            'args': {
                'fn': export_heats,
            },
        },
        {
            'id': 'json_classes',
            'name': 'JSON (Friendly) / Classes',
            'handlerFn': export_as_json,
            'args': {
                'fn': export_classes,
            },
        },
        {
            'id': 'json_formats',
            'name': 'JSON (Friendly) / Formats',
            'handlerFn': export_as_json,
            'args': {
                'fn': export_formats,
            },
        },
        {
            'id': 'json_results',
            'name': 'JSON (Friendly) / Results',
            'handlerFn': export_as_json,
            'args': {
                'fn': export_results,
            },
        },
        {
            'id': 'json_all',
            'name': 'JSON (Friendly) / All',
            'handlerFn': export_as_json,
            'args': {
                'fn': export_all,
            },
        },
    ]
