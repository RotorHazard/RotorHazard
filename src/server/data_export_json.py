'''JSON data exporter'''

import logging
logger = logging.getLogger(__name__)

import json
from sqlalchemy.ext.declarative import DeclarativeMeta

def export_as_json(DB, args):
    if 'fn' in args:
        payload = json.dumps(args['fn'](DB), indent='\t', cls=AlchemyEncoder)

        return {
            'data': payload,
            'encoding': 'application/json',
            'ext': 'json'
        }
    else:
        return False

def export_pilots(DB):
    pilots = DB.Pilot.query.all()
    payload = []
    for pilot in pilots:
        payload.append(pilot)

    return payload

def export_heats(DB):
    payload = {}
    for heat in DB.Heat.query.all():
        heat_id = heat.id
        note = heat.note
        race_class = heat.class_id

        heatnodes = DB.HeatNode.query.filter_by(heat_id=heat.id).all()
        pilots = {}
        for pilot in heatnodes:
            pilots[pilot.node_index] = pilot.pilot_id

        has_race = DB.SavedRaceMeta.query.filter_by(heat_id=heat.id).first()

        if has_race:
            locked = True
        else:
            locked = False

        payload[heat_id] = {
            'note': note,
            'heat_id': heat_id,
            'class_id': race_class,
            'nodes_pilots': pilots,
            'locked': locked
        }

    return payload

def export_classes(DB):
    race_classes = DB.RaceClass.query.all()
    payload = []
    for race_class in race_classes:
        payload.append(race_class)

    return payload

def export_formats(DB):
    formats = DB.RaceFormat.query.all()
    payload = []
    for race_format in formats:
        payload.append(race_format)

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
            'name': 'JSON / Pilots',
            'handlerFn': export_as_json,
            'args': {
                'fn': export_pilots,
            },
        },
        {
            'id': 'json_heats',
            'name': 'JSON / Heats',
            'handlerFn': export_as_json,
            'args': {
                'fn': export_heats,
            },
        },
        {
            'id': 'json_classes',
            'name': 'JSON / Classes',
            'handlerFn': export_as_json,
            'args': {
                'fn': export_classes,
            },
        },
        {
            'id': 'json_formats',
            'name': 'JSON / Formats',
            'handlerFn': export_as_json,
            'args': {
                'fn': export_formats,
            },
        },
    ]
