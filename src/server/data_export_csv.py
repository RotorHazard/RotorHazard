'''CSV data exporter'''

import logging
logger = logging.getLogger(__name__)
from Language import __
import RHUtils
import io
import csv
from sqlalchemy.ext.declarative import DeclarativeMeta
from data_export import DataExporter

def write_csv(data):
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows(data)

    return {
        'data': output.getvalue(),
        'encoding': 'text/csv',
        'ext': 'csv'
    }

def assemble_all(Database, PageCache):
    payload = {}
    payload['Pilots'] = assemble_pilots(Database, PageCache)
    payload['Heats'] = assemble_heats(Database, PageCache)
    payload['Classes'] = assemble_classes(Database, PageCache)
    payload['Formats'] = assemble_formats(Database, PageCache)
    payload['Results'] = assemble_results(Database, PageCache)

    output = []
    for datatype in payload:
        output.append([datatype])
        for data in payload[datatype]:
            output.append(data)
        output.append('')

    return output

def assemble_pilots(Database, PageCache):
    payload = [[__('Callsign'), __('Name'), __('Team')]]

    pilots = Database.Pilot.query.all()
    for pilot in pilots:
        payload.append([pilot.callsign, pilot.name, pilot.team])

    return payload

def assemble_heats(Database, PageCache):
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

def assemble_classes(Database, PageCache):
    race_classes = Database.RaceClass.query.all()
    payload = [[__('Name'), __('Description'), __('Race Format')]]

    for race_class in race_classes:
        # expand format id to name
        race_format = Database.RaceFormat.query.get(race_class.format_id)
        if race_format:
            format_string = race_format.name
        else:
            format_string = '-'

        payload.append([race_class.name, race_class.description, format_string])

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

def build_leaderboard(leaderboard, **kwargs):
    meta = leaderboard['meta']
    if 'primary_leaderboard' in kwargs and kwargs['primary_leaderboard'] in leaderboard:
        primary_leaderboard = leaderboard[kwargs['primary_leaderboard']]
    else:
        primary_leaderboard = leaderboard[meta['primary_leaderboard']]

    if meta['start_behavior'] == 2:
        total_label = __('Laps Total');
        total_source = 'total_time_laps'
    else:
        total_label = __('Total');
        total_source = 'total_time'

    output = [[
        __('Seat'),
        __('Rank'),
        __('Pilot'),
        __('Laps'),
        __(total_label),
        __('Avg.'),
        __('Fastest'),
        __('3 Consecutive'),
        __('Team'),
    ]]

    for entry in primary_leaderboard:
        output.append([
            entry['node'],
            entry['position'],
            entry['callsign'],
            entry['laps'],
            entry[total_source],
            entry['average_lap'],
            entry['fastest_lap'],
            entry['consecutives'],
            entry['team_name'],
         ])

    return output

def assemble_results(Database, PageCache):
    results = PageCache.data
    payload = []

    payload.append([__('Event Leaderboards') + ': ' + __('Race Totals')])
    for row in build_leaderboard(results['event_leaderboard'], primary_leaderboard='by_race_time'):
        payload.append(row[1:])

    payload.append([''])
    payload.append([__('Event Leaderboards') + ': ' + __('Fastest Laps')])
    for row in build_leaderboard(results['event_leaderboard'], primary_leaderboard='by_fastest_lap'):
        payload.append(row[1:])

    payload.append([''])
    payload.append([__('Event Leaderboards') + ': ' + __('Fastest 3 Consecutive Laps')])
    for row in build_leaderboard(results['event_leaderboard'], primary_leaderboard='by_consecutives'):
        payload.append(row[1:])

    payload.append([''])
    payload.append([__('Class Leaderboards')])

    # move unclassified heats to end
    all_classes = sorted(list(results['heats_by_class'].keys()))
    all_classes.append(all_classes.pop(all_classes.index(0)))

    for class_id in all_classes:

        valid_heats = False;
        if len(results['heats_by_class'][class_id]):
            for heat in results['heats_by_class'].keys():
                if heat in results['heats']:
                    valid_heats = True
                    break

        if valid_heats:
            if class_id in results['classes']:
                race_class = results['classes'][class_id]
            else:
                race_class = False

            payload.append([])
            if race_class:
                payload.append([__('Class') + ': ' + race_class['name']])
                payload.append([])
                payload.append([__('Class Summary')])
                for row in build_leaderboard(race_class['leaderboard']):
                    payload.append(row[1:])
            else:
                if len(results['classes']):
                    payload.append([__('Unclassified')])
                else:
                    payload.append([__('Heats')])

            for heat_id in results['heats_by_class'][class_id]:
                if heat_id in results['heats']:
                    heat = results['heats'][heat_id]

                    payload.append([])
                    if heat['note']:
                        payload.append([__('Heat') + ': ' + heat['note']])
                    else:
                        payload.append([__('Heat') + ' ' + str(heat_id)])

                    if len(heat['rounds']) > 1:
                        payload.append([])
                        payload.append([__('Heat Summary')])

                        for row in build_leaderboard(heat['leaderboard']):
                            payload.append(row[1:])

                    for heat_round in heat['rounds']:
                        payload.append([])
                        payload.append([__('Round {0}').format(heat_round['id'])])

                        laptimes = []

                        for row in build_leaderboard(heat_round['leaderboard']):
                            for node in heat_round['nodes']:
                                if row[0] == node['node_index']:
                                    laplist = []

                                    laplist.append(node['callsign'])

                                    for lap in node['laps']:
                                        if not lap['deleted']:
                                            laplist.append(lap['lap_time_formatted'])

                                    laptimes.append(laplist)

                            payload.append(row[1:])


                        payload.append([])
                        payload.append([__('Round {0} Times').format(str(heat_round['id']))])

                        for row in laptimes:
                            payload.append(row)

    return payload

def discover(*args, **kwargs):
    # returns array of exporters with default arguments
    return [
        DataExporter(
            'csv_pilots',
            'CSV (Friendly) / Pilots',
            write_csv,
            assemble_pilots
        ),
        DataExporter(
            'csv_heats',
            'CSV (Friendly) / Heats',
            write_csv,
            assemble_heats
        ),
        DataExporter(
            'csv_classes',
            'CSV (Friendly) / Classes',
            write_csv,
            assemble_classes
        ),
        DataExporter(
            'csv_formats',
            'CSV (Friendly) / Formats',
            write_csv,
            assemble_formats
        ),
        DataExporter(
            'csv_results',
            'CSV (Friendly) / Results',
            write_csv,
            assemble_results
        ),
        DataExporter(
            'csv_all',
            'CSV (Friendly) / All',
            write_csv,
            assemble_all
        )
    ]
