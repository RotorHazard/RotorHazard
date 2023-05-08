'''CSV data exporter'''

import logging
import RHUtils
import io
import csv
from data_export import DataExporter

logger = logging.getLogger(__name__)

def registerHandlers(args):
    if 'registerFn' in args:
        for exporter in discover():
            args['registerFn'](exporter)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('Export_Initialize', 'Export_register_CSV', registerHandlers, {}, 75, True)

def write_csv(data):
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows(data)

    return {
        'data': output.getvalue(),
        'encoding': 'text/csv',
        'ext': 'csv'
    }

def assemble_all(RaceContext):
    payload = {}
    payload['Pilots'] = assemble_pilots(RaceContext)
    payload['Heats'] = assemble_heats(RaceContext)
    payload['Classes'] = assemble_classes(RaceContext)
    payload['Formats'] = assemble_formats(RaceContext)
    payload['Results'] = assemble_results(RaceContext)

    output = []
    for datatype in payload:
        output.append([datatype])
        for data in payload[datatype]:
            output.append(data)
        output.append('')

    return output

def assemble_pilots(RaceContext):
    payload = [[RaceContext.language.__('Callsign'), RaceContext.language.__('Name'), RaceContext.language.__('Team')]]

    pilots = RaceContext.rhdata.get_pilots()
    for pilot in pilots:
        payload.append([pilot.callsign, pilot.name, pilot.team])

    return payload

def assemble_heats(RaceContext):
    payload = [[RaceContext.language.__('Name'), RaceContext.language.__('Class'), RaceContext.language.__('Pilots')]]
    for heat in RaceContext.rhdata.get_heats():
        displayname = heat.displayname()

        if heat.class_id != RHUtils.CLASS_ID_NONE:
            race_class = RaceContext.rhdata.get_raceClass(heat.class_id).name
        else:
            race_class = None

        row = [displayname, race_class]

        heatnodes = RaceContext.rhdata.get_heatNodes_by_heat(heat.id)
        for heatnode in heatnodes:
            if heatnode.pilot_id != RHUtils.PILOT_ID_NONE:
                row.append(RaceContext.rhdata.get_pilot(heatnode.pilot_id).callsign)
            else:
                row.append('-')

        payload.append(row)

    return payload

def assemble_classes(RaceContext):
    race_classes = RaceContext.rhdata.get_raceClasses()
    payload = [[RaceContext.language.__('Name'), RaceContext.language.__('Description'), RaceContext.language.__('Race Format')]]

    for race_class in race_classes:
        # expand format id to name
        race_format = RaceContext.rhdata.get_raceFormat(race_class.format_id)
        if race_format:
            format_string = race_format.name
        else:
            format_string = '-'

        payload.append([race_class.name, race_class.description, format_string])

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
    win_conditions = [
        RaceContext.language.__('None'),
        RaceContext.language.__('Most Laps in Fastest Time'),
        RaceContext.language.__('First to X Laps'),
        RaceContext.language.__('Fastest Lap'),
        RaceContext.language.__('Fastest Consecutive Laps'),
        RaceContext.language.__('Most Laps Only'),
        RaceContext.language.__('Most Laps Only with Overtime')
    ]
    start_behaviors = [
        RaceContext.language.__('Hole Shot'),
        RaceContext.language.__('First Lap'),
        RaceContext.language.__('Staggered Start'),
    ]

    formats = RaceContext.rhdata.get_raceFormats()
    payload = [[
        RaceContext.language.__('Name'),
        RaceContext.language.__('Race Clock Mode'),
        RaceContext.language.__('Timer Duration (seconds)'),
        RaceContext.language.__('Minimum Start Delay'),
        RaceContext.language.__('Maximum Start Delay'),
        RaceContext.language.__('Staging Tones'),
        RaceContext.language.__('First Crossing'),
        RaceContext.language.__('Win Condition'),
        RaceContext.language.__('Number of Laps to Win'),
        RaceContext.language.__('Team Racing Mode'),
    ]]

    for race_format in formats:
        payload.append([race_format.name,
            timer_modes[race_format.race_mode],
            race_format.race_time_sec,
            race_format.start_delay_min_ms,
            race_format.start_delay_max_ms,
            tones[race_format.staging_tones],
            start_behaviors[race_format.start_behavior],
            win_conditions[race_format.win_condition],
            race_format.number_laps_win,
            race_format.team_racing_mode,
        ])

    return payload

def build_leaderboard(leaderboard, RaceContext, **kwargs):
    meta = leaderboard['meta']
    if 'primary_leaderboard' in kwargs and kwargs['primary_leaderboard'] in leaderboard:
        primary_leaderboard = leaderboard[kwargs['primary_leaderboard']]
    else:
        primary_leaderboard = leaderboard[meta['primary_leaderboard']]

    if meta['start_behavior'] == 2:
        total_label = RaceContext.language.__('Laps Total')
        total_source = 'total_time_laps'
    else:
        total_label = RaceContext.language.__('Total')
        total_source = 'total_time'

    output = [[
        RaceContext.language.__('Seat'),
        RaceContext.language.__('Rank'),
        RaceContext.language.__('Pilot'),
        RaceContext.language.__('Laps'),
        RaceContext.language.__(total_label),
        RaceContext.language.__('Avg.'),
        RaceContext.language.__('Fastest'),
        RaceContext.language.__('Consecutive'),
        RaceContext.language.__('Team'),
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

def assemble_results(RaceContext):
    results = RaceContext.pagecache.get_cache()
    payload = []

    payload.append([RaceContext.language.__('Event Leaderboards') + ': ' + RaceContext.language.__('Race Totals')])
    for row in build_leaderboard(results['event_leaderboard'], RaceContext, primary_leaderboard='by_race_time'):
        payload.append(row[1:])

    payload.append([''])
    payload.append([RaceContext.language.__('Event Leaderboards') + ': ' + RaceContext.language.__('Fastest Laps')])
    for row in build_leaderboard(results['event_leaderboard'], RaceContext, primary_leaderboard='by_fastest_lap'):
        payload.append(row[1:])

    payload.append([''])
    payload.append([RaceContext.language.__('Event Leaderboards') + ': ' + RaceContext.language.__('Fastest Consecutive Laps')])
    for row in build_leaderboard(results['event_leaderboard'], RaceContext, primary_leaderboard='by_consecutives'):
        payload.append(row[1:])

    payload.append([''])
    payload.append([RaceContext.language.__('Class Leaderboards')])

    # move unclassified heats to end
    all_classes = sorted(list(results['heats_by_class'].keys()))
    all_classes.append(all_classes.pop(all_classes.index(0)))

    for class_id in all_classes:

        valid_heats = False
        if len(results['heats_by_class'][class_id]):
            for heat in results['heats_by_class'][class_id]:
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
                payload.append([RaceContext.language.__('Class') + ': ' + race_class['name']])
                payload.append([])
                payload.append([RaceContext.language.__('Class Summary')])
                for row in build_leaderboard(race_class['leaderboard'], RaceContext):
                    payload.append(row[1:])
            else:
                if len(results['classes']):
                    payload.append([RaceContext.language.__('Unclassified')])
                else:
                    payload.append([RaceContext.language.__('Heats')])

            for heat_id in results['heats_by_class'][class_id]:
                if heat_id in results['heats']:
                    heat = results['heats'][heat_id]

                    payload.append([])

                    payload.append(heat['displayname'])

                    if len(heat['rounds']) > 1:
                        payload.append([])
                        payload.append([RaceContext.language.__('Heat Summary')])

                        for row in build_leaderboard(heat['leaderboard'], RaceContext):
                            payload.append(row[1:])

                    for heat_round in heat['rounds']:
                        payload.append([])
                        payload.append([RaceContext.language.__('Round {0}').format(heat_round['id'])])

                        laptimes = []

                        for row in build_leaderboard(heat_round['leaderboard'], RaceContext):
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
                        payload.append([RaceContext.language.__('Round {0} Times').format(str(heat_round['id']))])

                        for row in laptimes:
                            payload.append(row)

    return payload

def discover(*_args, **_kwargs):
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
