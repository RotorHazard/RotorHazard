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

def assemble_all(RHData, PageCache, Language):
    payload = {}
    payload['Pilots'] = assemble_pilots(RHData, PageCache, Language)
    payload['Heats'] = assemble_heats(RHData, PageCache, Language)
    payload['Classes'] = assemble_classes(RHData, PageCache, Language)
    payload['Formats'] = assemble_formats(RHData, PageCache, Language)
    payload['Results'] = assemble_results(RHData, PageCache, Language)

    output = []
    for datatype in payload:
        output.append([datatype])
        for data in payload[datatype]:
            output.append(data)
        output.append('')

    return output

def assemble_pilots(RHData, _PageCache, Language):
    payload = [[Language.__('Callsign'), Language.__('Name'), Language.__('Team')]]

    pilots = RHData.get_pilots()
    for pilot in pilots:
        payload.append([pilot.callsign, pilot.name, pilot.team])

    return payload

def assemble_heats(RHData, _PageCache, Language):
    payload = [[Language.__('Name'), Language.__('Class'), Language.__('Pilots')]]
    for heat in RHData.get_heats():
        displayname = heat.displayname()

        if heat.class_id != RHUtils.CLASS_ID_NONE:
            race_class = RHData.get_raceClass(heat.class_id).name
        else:
            race_class = None

        row = [displayname, race_class]

        heatnodes = RHData.get_heatNodes_by_heat(heat.id)
        for heatnode in heatnodes:
            if heatnode.pilot_id != RHUtils.PILOT_ID_NONE:
                row.append(RHData.get_pilot(heatnode.pilot_id).callsign)
            else:
                row.append('-')

        payload.append(row)

    return payload

def assemble_classes(RHData, _PageCache, Language):
    race_classes = RHData.get_raceClasses()
    payload = [[Language.__('Name'), Language.__('Description'), Language.__('Race Format')]]

    for race_class in race_classes:
        # expand format id to name
        race_format = RHData.get_raceFormat(race_class.format_id)
        if race_format:
            format_string = race_format.name
        else:
            format_string = '-'

        payload.append([race_class.name, race_class.description, format_string])

    return payload

def assemble_formats(RHData, _PageCache, Language):
    timer_modes = [
        Language.__('Fixed Time'),
        Language.__('No Time Limit'),
    ]
    tones = [
        Language.__('None'),
        Language.__('One'),
        Language.__('Each Second')
    ]
    win_conditions = [
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
    payload = [[
        Language.__('Name'),
        Language.__('Race Clock Mode'),
        Language.__('Timer Duration (seconds)'),
        Language.__('Minimum Start Delay'),
        Language.__('Maximum Start Delay'),
        Language.__('Staging Tones'),
        Language.__('First Crossing'),
        Language.__('Win Condition'),
        Language.__('Number of Laps to Win'),
        Language.__('Team Racing Mode'),
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

def build_leaderboard(leaderboard, Language, **kwargs):
    meta = leaderboard['meta']
    if 'primary_leaderboard' in kwargs and kwargs['primary_leaderboard'] in leaderboard:
        primary_leaderboard = leaderboard[kwargs['primary_leaderboard']]
    else:
        primary_leaderboard = leaderboard[meta['primary_leaderboard']]

    if meta['start_behavior'] == 2:
        total_label = Language.__('Laps Total')
        total_source = 'total_time_laps'
    else:
        total_label = Language.__('Total')
        total_source = 'total_time'

    output = [[
        Language.__('Seat'),
        Language.__('Rank'),
        Language.__('Pilot'),
        Language.__('Laps'),
        Language.__(total_label),
        Language.__('Avg.'),
        Language.__('Fastest'),
        Language.__('3 Consecutive'),
        Language.__('Team'),
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

def assemble_results(_RHData, PageCache, Language):
    results = PageCache.get_cache()
    payload = []

    payload.append([Language.__('Event Leaderboards') + ': ' + Language.__('Race Totals')])
    for row in build_leaderboard(results['event_leaderboard'], Language, primary_leaderboard='by_race_time'):
        payload.append(row[1:])

    payload.append([''])
    payload.append([Language.__('Event Leaderboards') + ': ' + Language.__('Fastest Laps')])
    for row in build_leaderboard(results['event_leaderboard'], Language, primary_leaderboard='by_fastest_lap'):
        payload.append(row[1:])

    payload.append([''])
    payload.append([Language.__('Event Leaderboards') + ': ' + Language.__('Fastest 3 Consecutive Laps')])
    for row in build_leaderboard(results['event_leaderboard'], Language, primary_leaderboard='by_consecutives'):
        payload.append(row[1:])

    payload.append([''])
    payload.append([Language.__('Class Leaderboards')])

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
                payload.append([Language.__('Class') + ': ' + race_class['name']])
                payload.append([])
                payload.append([Language.__('Class Summary')])
                for row in build_leaderboard(race_class['leaderboard'], Language):
                    payload.append(row[1:])
            else:
                if len(results['classes']):
                    payload.append([Language.__('Unclassified')])
                else:
                    payload.append([Language.__('Heats')])

            for heat_id in results['heats_by_class'][class_id]:
                if heat_id in results['heats']:
                    heat = results['heats'][heat_id]

                    payload.append([])

                    payload.append(heat['displayname'])

                    if len(heat['rounds']) > 1:
                        payload.append([])
                        payload.append([Language.__('Heat Summary')])

                        for row in build_leaderboard(heat['leaderboard'], Language):
                            payload.append(row[1:])

                    for heat_round in heat['rounds']:
                        payload.append([])
                        payload.append([Language.__('Round {0}').format(heat_round['id'])])

                        laptimes = []

                        for row in build_leaderboard(heat_round['leaderboard'], Language):
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
                        payload.append([Language.__('Round {0} Times').format(str(heat_round['id']))])

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
