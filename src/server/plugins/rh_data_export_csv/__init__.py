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
        kwargs['Events'].on('Export_Initialize', 'Export_register_CSV', registerHandlers, {}, 75)

def write_csv(data):
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows(data)

    return {
        'data': output.getvalue(),
        'encoding': 'text/csv',
        'ext': 'csv'
    }

def assemble_all(RHAPI):
    payload = {}
    payload['Pilots'] = assemble_pilots(RHAPI)
    payload['Heats'] = assemble_heats(RHAPI)
    payload['Classes'] = assemble_classes(RHAPI)
    payload['Formats'] = assemble_formats(RHAPI)
    payload['Results'] = assemble_results(RHAPI)

    output = []
    for datatype in payload:
        output.append([datatype])
        for data in payload[datatype]:
            output.append(data)
        output.append('')

    return output

def assemble_pilots(RHAPI):
    payload = [[RHAPI.__('Callsign'), RHAPI.__('Name'), RHAPI.__('Team')]]

    pilots = RHAPI.db.pilots
    for pilot in pilots:
        payload.append([pilot.callsign, pilot.name, pilot.team])

    return payload

def assemble_heats(RHAPI):
    payload = [[RHAPI.__('Name'), RHAPI.__('Class'), RHAPI.__('Pilots')]]
    for heat in RHAPI.db.heats:
        displayname = heat.display_name()

        if heat.class_id != RHUtils.CLASS_ID_NONE:
            race_class_name = RHAPI.db.raceclass_by_id(heat.class_id).name
        else:
            race_class_name = None

        row = [displayname, race_class_name]

        heatnodes = RHAPI.db.slots_by_heat(heat.id)
        for heatnode in heatnodes:
            if heatnode.pilot_id != RHUtils.PILOT_ID_NONE:
                row.append(RHAPI.db.pilot_by_id(heatnode.pilot_id).callsign)
            else:
                row.append('-')

        payload.append(row)

    return payload

def assemble_classes(RHAPI):
    race_classes = RHAPI.db.raceclasses
    payload = [[RHAPI.__('Name'), RHAPI.__('Description'), RHAPI.__('Race Format')]]

    for race_class in race_classes:
        # expand format id to name
        race_format = RHAPI.db.raceformat_by_id(race_class.format_id)
        if race_format:
            format_string = race_format.name
        else:
            format_string = '-'

        payload.append([race_class.name, race_class.description, format_string])

    return payload

def assemble_formats(RHAPI):
    timer_modes = [
        RHAPI.__('Fixed Time'),
        RHAPI.__('No Time Limit'),
    ]
    tones = [
        RHAPI.__('None'),
        RHAPI.__('One'),
        RHAPI.__('Each Second')
    ]
    win_conditions = [
        RHAPI.__('None'),
        RHAPI.__('Most Laps in Fastest Time'),
        RHAPI.__('First to X Laps'),
        RHAPI.__('Fastest Lap'),
        RHAPI.__('Fastest Consecutive Laps'),
        RHAPI.__('Most Laps Only'),
        RHAPI.__('Most Laps Only with Overtime')
    ]
    start_behaviors = [
        RHAPI.__('Hole Shot'),
        RHAPI.__('First Lap'),
        RHAPI.__('Staggered Start'),
    ]

    formats = RHAPI.db.raceformats
    payload = [[
        RHAPI.__('Name'),
        RHAPI.__('Race Clock Mode'),
        RHAPI.__('Timer Duration (seconds)'),
        RHAPI.__('Minimum Start Delay'),
        RHAPI.__('Maximum Start Delay'),
        RHAPI.__('Staging Tones'),
        RHAPI.__('First Crossing'),
        RHAPI.__('Win Condition'),
        RHAPI.__('Number of Laps to Win'),
        RHAPI.__('Team Racing Mode'),
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

def build_leaderboard(leaderboard, RHAPI, **kwargs):
    if not leaderboard:
        return None

    meta = leaderboard['meta']
    if 'primary_leaderboard' in kwargs and kwargs['primary_leaderboard'] in leaderboard:
        primary_leaderboard = leaderboard[kwargs['primary_leaderboard']]
    else:
        primary_leaderboard = leaderboard[meta['primary_leaderboard']]

    if meta['start_behavior'] == 2:
        total_label = RHAPI.__('Laps Total')
        total_source = 'total_time_laps'
    else:
        total_label = RHAPI.__('Total')
        total_source = 'total_time'

    output = [[
        RHAPI.__('Seat'),
        RHAPI.__('Rank'),
        RHAPI.__('Pilot'),
        RHAPI.__('Laps'),
        RHAPI.__(total_label),
        RHAPI.__('Avg.'),
        RHAPI.__('Fastest'),
        RHAPI.__('Consecutive'),
        RHAPI.__('Team'),
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
            F"{entry['consecutives_base']}/{entry['consecutives']}",
            entry['team_name'],
         ])

    return output

def assemble_results(RHAPI):
    results = RHAPI.eventresults.results

    if not results:
        return None

    payload = []

    if results['event_leaderboard']:
        payload.append([RHAPI.__('Event Leaderboards') + ': ' + RHAPI.__('Race Totals')])
        for row in build_leaderboard(results['event_leaderboard'], RHAPI, primary_leaderboard='by_race_time'):
            payload.append(row[1:])

        payload.append([''])
        payload.append([RHAPI.__('Event Leaderboards') + ': ' + RHAPI.__('Fastest Laps')])
        for row in build_leaderboard(results['event_leaderboard'], RHAPI, primary_leaderboard='by_fastest_lap'):
            payload.append(row[1:])
    
        payload.append([''])
        payload.append([RHAPI.__('Event Leaderboards') + ': ' + RHAPI.__('Fastest Consecutive Laps')])
        for row in build_leaderboard(results['event_leaderboard'], RHAPI, primary_leaderboard='by_consecutives'):
            payload.append(row[1:])

        payload.append([''])

    all_classes = sorted(list(results['heats_by_class'].keys()))

    if all_classes:
        payload.append([RHAPI.__('Class Leaderboards')])

        # move unclassified heats to end
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
                    payload.append([RHAPI.__('Class') + ': ' + race_class['name']])
                    payload.append([])
                    payload.append([RHAPI.__('Class Summary')])
                    for row in build_leaderboard(race_class['leaderboard'], RHAPI):
                        payload.append(row[1:])
                else:
                    if len(results['classes']):
                        payload.append([RHAPI.__('Unclassified')])
                    else:
                        payload.append([RHAPI.__('Heats')])

                for heat_id in results['heats_by_class'][class_id]:
                    if heat_id in results['heats']:
                        heat = results['heats'][heat_id]

                        payload.append([])

                        payload.append([heat['displayname']])

                        if len(heat['rounds']) > 1:
                            payload.append([])
                            payload.append([RHAPI.__('Heat Summary')])

                            for row in build_leaderboard(heat['leaderboard'], RHAPI):
                                payload.append(row[1:])

                        for heat_round in heat['rounds']:
                            payload.append([])
                            payload.append([RHAPI.__('Round {0}').format(heat_round['id'])])

                            laptimes = []

                            for row in build_leaderboard(heat_round['leaderboard'], RHAPI):
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
                            payload.append([RHAPI.__('Round {0} Times').format(str(heat_round['id']))])

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
