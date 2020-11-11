'''CSV data exporter'''

import logging
logger = logging.getLogger(__name__)
from Language import __
import RHUtils
import io
import csv
from sqlalchemy.ext.declarative import DeclarativeMeta

def export_as_csv(Database, PageCache, args):
    if 'fn' in args:
        payload = args['fn'](Database, PageCache)

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerows(payload)

        return {
            'data': output.getvalue(),
            'encoding': 'application/json',
            'ext': 'csv'
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

    output = []
    for datatype in payload:
        output.append([datatype])
        for data in payload[datatype]:
            output.append(data)
        output.append('')

    return output

def export_pilots(Database, PageCache):
    payload = [[__('Callsign'), __('Name'), __('Team')]]

    pilots = Database.Pilot.query.all()
    for pilot in pilots:
        payload.append([pilot.callsign, pilot.name, pilot.team])

    return payload

def export_heats(Database, PageCache):
    payload = [[__('Name'), __('Class'), __('Pilots')]]
    for heat in Database.Heat.query.all():
        heat_id = heat.id
        note = heat.note

        if heat.class_id != RHUtils.CLASS_ID_NONE:
            race_class = Database.RaceClass.query.get(heat.class_id).name
        else:
            race_class = None

        row = [note, race_class]

        heatnodes = Database.HeatNode.query.filter_by(heat_id=heat.id).order_by(Database.HeatNode.node_index).all()
        pilots = {}
        for heatnode in heatnodes:
            if heatnode.pilot_id != RHUtils.PILOT_ID_NONE:
                row.append(Database.Pilot.query.get(heatnode.pilot_id).callsign)
            else:
                row.append('-')

        payload.append(row)

    return payload

def export_classes(Database, PageCache):
    race_classes = Database.RaceClass.query.all()
    payload = [[__('Name'), __('Description'), __('Race Format')]]

    for race_class in race_classes:
        # expand format id to name
        payload.append([race_class.name, race_class.description, Database.RaceFormat.query.get(race_class.format_id).name])

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
    payload = [[
        __('Name'),
        __('Race Clock Mode'),
        __('Timer Duration (seconds)'),
        __('Minimum Start Delay'),
        __('Maximum Start Delay'),
        __('Staging Tones'),
        __('First Crossing'),
        __('Win Condition'),
        __('Number of Laps to Win'),
        __('Team Racing Mode'),
    ]]

    for race_format in formats:
        payload.append([race_format.name,
            timer_modes[race_format.race_mode],
            race_format.race_time_sec,
            race_format.start_delay_min,
            race_format.start_delay_max,
            tones[race_format.staging_tones],
            start_behaviors[race_format.start_behavior],
            race_format.win_condition,
            race_format.number_laps_win,
            race_format.team_racing_mode,
        ])

    return payload

def export_results(Database, PageCache):
    #payload = PageCache.data
    payload = [[None]]
    return payload

def discover(*args, **kwargs):
    # returns array of exporters with default arguments
    return [
        {
            'id': 'csv_pilots',
            'name': 'CSV (Friendly) / Pilots',
            'handlerFn': export_as_csv,
            'args': {
                'fn': export_pilots,
            },
        },
        {
            'id': 'csv_heats',
            'name': 'CSV (Friendly) / Heats',
            'handlerFn': export_as_csv,
            'args': {
                'fn': export_heats,
            },
        },
        {
            'id': 'csv_classes',
            'name': 'CSV (Friendly) / Classes',
            'handlerFn': export_as_csv,
            'args': {
                'fn': export_classes,
            },
        },
        {
            'id': 'csv_formats',
            'name': 'CSV (Friendly) / Formats',
            'handlerFn': export_as_csv,
            'args': {
                'fn': export_formats,
            },
        },
        {
            'id': 'csv_results',
            'name': 'CSV (Friendly) / Results',
            'handlerFn': export_as_csv,
            'args': {
                'fn': export_results,
            },
        },
        {
            'id': 'csv_all',
            'name': 'CSV (Friendly) / All',
            'handlerFn': export_as_csv,
            'args': {
                'fn': export_all,
            },
        },
    ]
