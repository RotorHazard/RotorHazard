'''CSV data exporter'''

import logging
import RHUtils
import io
import csv
from eventmanager import Evt
from data_export import DataExporter

logger = logging.getLogger(__name__)

def write_csv(data):
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows(data)

    return {
        'data': output.getvalue(),
        'encoding': 'text/csv',
        'ext': 'csv'
    }

def assemble_all(rhapi):
    payload = {}
    payload['Pilots'] = assemble_pilots(rhapi)
    payload['Heats'] = assemble_heats(rhapi)
    payload['Classes'] = assemble_classes(rhapi)
    payload['Formats'] = assemble_formats(rhapi)
    payload['Results'] = assemble_results(rhapi)

    output = []
    for datatype in payload:
        output.append([datatype])
        for data in payload[datatype]:
            output.append(data)
        output.append('')

    return output

def assemble_pilots(rhapi):
    payload = [[rhapi.__('Callsign'), rhapi.__('Name'), rhapi.__('Team')]]

    pilots = rhapi.db.pilots
    for pilot in pilots:
        payload.append([pilot.callsign, pilot.name, pilot.team])

    return payload

def assemble_heats(rhapi):
    payload = [[rhapi.__('Name'), rhapi.__('Class'), rhapi.__('Pilots')]]
    for heat in rhapi.db.heats:
        displayname = heat.display_name()

        if heat.class_id != RHUtils.CLASS_ID_NONE:
            race_class_name = rhapi.db.raceclass_by_id(heat.class_id).name
        else:
            race_class_name = None

        row = [displayname, race_class_name]

        heatnodes = rhapi.db.slots_by_heat(heat.id)
        for heatnode in heatnodes:
            if heatnode.pilot_id != RHUtils.PILOT_ID_NONE:
                row.append(rhapi.db.pilot_by_id(heatnode.pilot_id).callsign)
            else:
                row.append('-')

        payload.append(row)

    return payload

def assemble_classes(rhapi):
    race_classes = rhapi.db.raceclasses
    payload = [[rhapi.__('Name'), rhapi.__('Description'), rhapi.__('Race Format')]]

    for race_class in race_classes:
        # expand format id to name
        race_format = rhapi.db.raceformat_by_id(race_class.format_id)
        if race_format:
            format_string = race_format.name
        else:
            format_string = '-'

        payload.append([race_class.name, race_class.description, format_string])

    return payload

def assemble_formats(rhapi):
    timer_modes = [
        rhapi.__('Fixed Time'),
        rhapi.__('No Time Limit'),
    ]
    tones = [
        rhapi.__('None'),
        rhapi.__('One'),
        rhapi.__('Each Second')
    ]
    win_conditions = [
        rhapi.__('None'),
        rhapi.__('Most Laps in Fastest Time'),
        rhapi.__('First to X Laps'),
        rhapi.__('Fastest Lap'),
        rhapi.__('Fastest Consecutive Laps'),
        rhapi.__('Most Laps Only'),
        rhapi.__('Most Laps Only with Overtime')
    ]
    start_behaviors = [
        rhapi.__('Hole Shot'),
        rhapi.__('First Lap'),
        rhapi.__('Staggered Start'),
    ]

    formats = rhapi.db.raceformats
    payload = [[
        rhapi.__('Name'),
        rhapi.__('Race Clock Mode'),
        rhapi.__('Timer Duration (seconds)'),
        rhapi.__('Minimum Start Delay'),
        rhapi.__('Maximum Start Delay'),
        rhapi.__('Staging Tones'),
        rhapi.__('First Crossing'),
        rhapi.__('Win Condition'),
        rhapi.__('Number of Laps to Win'),
        rhapi.__('Team Racing Mode'),
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

def build_leaderboard(leaderboard, rhapi, **kwargs):
    if not leaderboard:
        return None

    meta = leaderboard['meta']
    if 'primary_leaderboard' in kwargs and kwargs['primary_leaderboard'] in leaderboard:
        primary_leaderboard = leaderboard[kwargs['primary_leaderboard']]
    else:
        primary_leaderboard = leaderboard[meta['primary_leaderboard']]

    if meta['start_behavior'] == 2:
        total_label = rhapi.__('Laps Total')
        total_source = 'total_time_laps'
    else:
        total_label = rhapi.__('Total')
        total_source = 'total_time'

    output = [[
        rhapi.__('Seat'),
        rhapi.__('Rank'),
        rhapi.__('Pilot'),
        rhapi.__('Laps'),
        rhapi.__(total_label),
        rhapi.__('Avg.'),
        rhapi.__('Fastest'),
        rhapi.__('Consecutive'),
        rhapi.__('Team'),
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

def assemble_results(rhapi):
    results = rhapi.eventresults.results

    if not results:
        return None

    payload = []

    if results['event_leaderboard']:
        payload.append([rhapi.__("Event Leaderboards") + ": " + rhapi.__("Race Totals")])
        for row in build_leaderboard(results['event_leaderboard'], rhapi, primary_leaderboard='by_race_time'):
            payload.append(row[1:])

        payload.append([''])
        payload.append([rhapi.__("Event Leaderboards") + ": " + rhapi.__("Fastest Laps")])
        for row in build_leaderboard(results['event_leaderboard'], rhapi, primary_leaderboard='by_fastest_lap'):
            payload.append(row[1:])
    
        payload.append([''])
        payload.append([rhapi.__("Event Leaderboards") + ": " + rhapi.__("Fastest Consecutive Laps")])
        for row in build_leaderboard(results['event_leaderboard'], rhapi, primary_leaderboard='by_consecutives'):
            payload.append(row[1:])

        payload.append([''])

    all_classes = sorted(list(results['heats_by_class'].keys()))

    if all_classes:
        payload.append([rhapi.__('Class Leaderboards')])

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
                    payload.append([rhapi.__("Class") + ": " + race_class['name']])
                    payload.append([])
                    payload.append([rhapi.__("Class Summary")])
                    for row in build_leaderboard(race_class['leaderboard'], rhapi):
                        payload.append(row[1:])
                else:
                    if len(results['classes']):
                        payload.append([rhapi.__("Unclassified")])
                    else:
                        payload.append([rhapi.__("Heats")])

                for heat_id in results['heats_by_class'][class_id]:
                    if heat_id in results['heats']:
                        heat = results['heats'][heat_id]

                        payload.append([])

                        payload.append([heat['displayname']])

                        if len(heat['rounds']) > 1:
                            payload.append([])
                            payload.append([rhapi.__("Heat Summary")])

                            for row in build_leaderboard(heat['leaderboard'], rhapi):
                                payload.append(row[1:])

                        for heat_round in heat['rounds']:
                            payload.append([])
                            payload.append([rhapi.__("Round {0}").format(heat_round['id'])])

                            laptimes = []

                            for row in build_leaderboard(heat_round['leaderboard'], rhapi):
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
                            payload.append([rhapi.__("Round {0} Times").format(str(heat_round['id']))])

                            for row in laptimes:
                                payload.append(row)

    return payload

def register_handlers(args):
    for exporter in [
        DataExporter(
            'csv_pilots',
            "CSV (Friendly) / Pilots",
            write_csv,
            assemble_pilots
        ),
        DataExporter(
            'csv_heats',
            "CSV (Friendly) / Heats",
            write_csv,
            assemble_heats
        ),
        DataExporter(
            'csv_classes',
            "CSV (Friendly) / Classes",
            write_csv,
            assemble_classes
        ),
        DataExporter(
            'csv_formats',
            "CSV (Friendly) / Formats",
            write_csv,
            assemble_formats
        ),
        DataExporter(
            'csv_results',
            "CSV (Friendly) / Results",
            write_csv,
            assemble_results
        ),
        DataExporter(
            'csv_all',
            "CSV (Friendly) / All",
            write_csv,
            assemble_all
        )
    ]:
        args['register_fn'](exporter)

def initialize(**kwargs):
    kwargs['events'].on(Evt.DATA_EXPORT_INITIALIZE, 'Export_register_CSV', register_handlers, {}, 75)

