from enum import Enum
import itertools
import json
from . import RHRace
import numpy as np


UNCLASSIFIED = 'Unclassified'


class RaceObjective(str,Enum):
    FASTEST_CONSECUTIVE = 'fastest-consecutive'
    MOST_LAPS_QUICKEST_TIME = 'most-laps-quickest-time'


class LeaderboardMethod(str,Enum):
    BEST = 'best'


def export_results(RHData):
    event_name = RHData.get_option('eventName', '')
    msgs = []
    for race in RHData.get_savedRaceMetas():
        race_id = race.id
        round_idx = race.round_id - 1
        heat_id = race.heat_id
        heat = RHData.get_heat(heat_id)
        stage_id = heat.stage_id
        pilotraces = RHData.get_savedPilotRaces_by_savedRaceMeta(race.id)
        for pilotrace in pilotraces:
            pilot = RHData.get_pilot(pilotrace.pilot_id)
            if pilot:
                pilotlaps = RHData.get_savedRaceLaps_by_savedPilotRace(pilotrace.id)
                laps = []
                for lap_id,pilotlap in enumerate(pilotlaps):
                    laps.append({'lap': lap_id, 'timestamp': pilotlap.lap_time_stamp, 'location': 0})
                    lapsplits = RHData.get_lapSplits_by_lap(race_id, pilotrace.node_index, lap_id)
                    for lapsplit in lapsplits:
                        laps.append({'lap': lap_id, 'timestamp': lapsplit.split_time_stamp, 'location': lapsplit.split_id+1})
                msg = {'event': event_name, 'stage': 'id:'+str(stage_id), 'round': round_idx, 'heat': 'id:'+str(heat_id), 'pilot': pilot.callsign, 'laps': laps}
                msgs.append(msg)
    return msgs


def pilot_results(msgs):
    results = {'pilots': {}}
    results_by_pilot = results['pilots']
    for msg in msgs:
        eventName = msg['event']
        stageIdx = msg['stage']
        roundIdx = msg['round']
        heatIdx = msg['heat']
        pilot = msg['pilot']
        if pilot not in results_by_pilot:
            results_by_pilot[pilot] = {'events': {}}
        event_results = results_by_pilot[pilot]['events']
        if eventName not in event_results:
            event_results[eventName] = {'stages': {}}
        event_stages = event_results[eventName]['stages']
        if stageIdx not in event_stages:
            event_stages[stageIdx] = {'heats': {}}
        heats = event_stages[stageIdx]['heats']
        if heatIdx not in heats:
            heats[heatIdx] = {'rounds': []}
        rounds = heats[heatIdx]['rounds']
        while roundIdx >= len(rounds):
            rounds.append(None)
        rounds[roundIdx] = {'laps': msg['laps']}
    return results


def export_event(RHData):
    event_name = RHData.get_option('eventName', "")
    event_desc = RHData.get_option('eventDescription', "")
    event_url = RHData.get_option('eventURL', "")

    pilots = {}
    pilots_by_id = {}
    for pilot in RHData.get_pilots():
        pilots[pilot.callsign] = {'name': pilot.name}
        pilots_by_id[pilot.id] = pilot

    race_formats = {'Free': {'start': 'first-pass', 'duration': 0}}
    race_formats_by_id = {0: 'Free'}
    for race_format in RHData.get_raceFormats():
        race_formats[race_format.name] = export_race_format(race_format)
        race_formats_by_id[race_format.id] = race_format.name

    race_classes = {UNCLASSIFIED: {'description': "Default class"}}
    race_classes_by_id = {0: UNCLASSIFIED}
    for race_class in RHData.get_raceClasses():
        race_format_name = race_formats_by_id[race_class.format_id]
        race_classes[race_class.name] = {
            'description': race_class.description,
            'format': race_format_name,
            'children': {child.name: {} for child in race_class.children}
        }
        race_classes_by_id[race_class.id] = race_class.name

    seats = []
    current_profile = RHData.get_optionInt('currentProfile')
    profile = RHData.get_profile(current_profile)
    freqs = json.loads(profile.frequencies)
    for f_b_c in zip(freqs['f'], freqs['b'], freqs['c']):
        fbc = {'frequency': f_b_c[0]}
        if f_b_c[1] and f_b_c[2]:
            fbc['bandChannel'] = f_b_c[1] + str(f_b_c[2])
        seats.append(fbc)

    event_formats = {}
    event_classes = {}
    stages = []
    prev_stage_name = None
    for heat_idx, rhheat in enumerate(RHData.get_heats()):
        heat_seats = [None] * len(seats)
        for heat_node in RHData.get_heatNodes_by_heat(rhheat.id):
            if heat_node.node_index < len(heat_seats) and heat_node.pilot_id in pilots_by_id:
                heat_seats[heat_node.node_index] = pilots_by_id[heat_node.pilot_id].callsign
        race_name = rhheat.note if rhheat.note else 'Heat '+str(heat_idx+1)
        race_class_name = race_classes_by_id[rhheat.class_id]
        if race_class_name not in event_classes:
            race_class = race_classes[race_class_name]
            event_classes[race_class_name] = race_class
            race_format_name = race_class.get('format', None)
            if race_format_name is not None and race_format_name not in event_formats:
                event_formats[race_format_name] = race_formats[race_format_name]
        race = {
            'id': str(rhheat.id),
            'name': race_name,
            'class': race_class_name,
            'seats': heat_seats
        }
        stage_name = rhheat.stage.name
        if stage_name != prev_stage_name:
            races = []
            stage = {'id': str(rhheat.stage_id), 'name': stage_name, 'heats': races}
            stage.update(rhheat.stage.data)
            stages.append(stage)
            prev_stage_name = stage_name
        races.append(race)
    event_classes = RHData.get_optionJson('eventClasses', event_classes)
    data = {
        'name': event_name,
        'description': event_desc,
        'url': event_url,
        'pilots': pilots,
        'formats': event_formats,
        'classes': event_classes,
        'seats': seats,
        'stages': stages
    }
    return data


def export_race_format(race_format):
    start = 'start-line' if race_format.start_behavior == RHRace.StartBehavior.FIRST_LAP else 'first-pass'
    consecutive_laps = 0
    if race_format.win_condition == RHRace.WinCondition.FASTEST_3_CONSECUTIVE:
        objective = RaceObjective.FASTEST_CONSECUTIVE
        consecutive_laps = 3
    elif race_format.win_condition == RHRace.WinCondition.MOST_PROGRESS:
        objective = RaceObjective.MOST_LAPS_QUICKEST_TIME
    else:
        objective = None
    json = {
        'start': start,
        'duration': race_format.race_time_sec + race_format.lap_grace_sec,
        'objective': objective,
        'maxLaps': race_format.number_laps_win
    }
    if consecutive_laps:
        json['consecutiveLaps'] = consecutive_laps
    return json


def import_event(data, rhserver):
    event_name = data['name']
    race_classes = data['classes'] if 'classes' in data else {}
    seats = data['seats']
    pilots = data['pilots']
    stages = data['stages']

    RHData = rhserver['RHData']
    RHData.set_option('eventName', event_name)
    RHData.set_optionJson('eventClasses', race_classes)
    if 'description' in data:
        RHData.set_option('eventDescription', data['description'])
    if 'url' in data:
        RHData.set_option('eventURL', data['url'])

    profile_data = {'profile_name': event_name,
        'frequencies': {'b': [s['bandChannel'][0] if 'bandChannel' in s else None for s in seats],
                        'c': [int(s['bandChannel'][1]) if 'bandChannel' in s else None for s in seats],
                        'f': [s['frequency'] for s in seats]
                        }
        }
    profile = RHData.upsert_profile(profile_data)

    raceFormat_ids_by_name = {}
    for rhraceformat in RHData.get_raceFormats():
        raceFormat_ids_by_name[rhraceformat.name] = rhraceformat.id

    raceClass_ids = {}
    for rhraceclass in RHData.get_raceClasses():
        raceClass_ids[rhraceclass.name] = rhraceclass.id
    
    pilot_ids = {}
    for rhpilot in RHData.get_pilots():
        pilot_ids[rhpilot.callsign] = rhpilot.id

    for race_class_name, race_class in race_classes.items():
        raceClass_id = raceClass_ids.get(race_class_name, None)
        if not raceClass_id:
            class_data = {
                'name': race_class_name
            }
            if 'description' in race_class:
                class_data['description'] = race_class['description']
            raceFormat_name = race_class.get('format', None)
            if raceFormat_name in raceFormat_ids_by_name:
                class_data['format_id'] = raceFormat_ids_by_name[raceFormat_name]
            rhraceclass = RHData.add_raceClass(class_data)
            raceClass_ids[race_class_name] = rhraceclass.id

    for callsign, pilot in pilots.items():
        pilot_id = pilot_ids.get(callsign, None)
        if not pilot_id:
            pilot_data = {
                'callsign': callsign,
                'name': pilot['name']
            }
            if 'url' in pilot:
                pilot_data['url'] = pilot['url']
            rhpilot = RHData.add_pilot(pilot_data)
            pilot_ids[callsign] = rhpilot.id

    rhheats = RHData.get_heats()
    h = 0
    for stage in stages:
        rhheat = None
        for heat in stage['heats']:
            if h < len(rhheats):
                rhheat = rhheats[h]
                heat_nodes = RHData.get_heatNodes_by_heat(rhheat.id)
                for seat_index in range(len(heat_nodes), len(heat['seats'])):
                    RHData.add_heatNode(rhheat.id, seat_index)
                for seat,callsign in enumerate(heat['seats']):
                    if callsign in pilot_ids:
                        heat_data = {'heat': rhheat.id, 'note': heat['name'], 'stage': stage['name'], 'node': seat, 'pilot': pilot_ids[callsign]}
                        heat_class = heat.get('class', UNCLASSIFIED)
                        if heat_class != UNCLASSIFIED:
                            heat_data['class'] = raceClass_ids[heat_class]
                        RHData.alter_heat(heat_data)
            else:
                heat_data = {'note': heat['name'], 'stage': stage['name']}
                heat_class = heat.get('class', UNCLASSIFIED)
                if heat_class != UNCLASSIFIED:
                    heat_data['class'] = raceClass_ids[heat_class]
                heat_pilots = {}
                for seat,callsign in enumerate(heat['seats']):
                    if callsign in pilot_ids:
                        heat_pilots[seat] = pilot_ids[callsign]
                rhheat = RHData.add_heat(init=heat_data, initPilots=heat_pilots)
            h += 1

        if rhheat:
            stage_data = {}
            if 'type' in stage:
                stage_data['type'] = stage['type']
            if 'leaderboards' in stage:
                stage_data['leaderboards'] = stage['leaderboards']
            rhheat.stage.data = stage_data

    for i in range(len(rhheats)-1, h-1, -1):
        RHData.delete_heat(rhheats[i].id)

    RHData.commit()

    rhserver['on_set_profile']({'profile': profile.id})
    rhserver['emit_pilot_data']()
    rhserver['emit_heat_data']()


def calculate_metrics(results, event_data):
    event_name = event_data['name']
    for pilot_result in results['pilots'].values():
        event_result = pilot_result['events'].get(event_name, {})
        for stage_idx, stage_result in event_result['stages'].items():
            stage_info = lookup_by_index_or_id(event_data['stages'], stage_idx)
            stage_classes = set()
            for heat_idx, heat_result in stage_result['heats'].items():
                if stage_info:
                    heat_info = lookup_by_index_or_id(stage_info['heats'], heat_idx)
                    race_class_name = heat_info['class']
                    heat_result['class'] = race_class_name
                    race_class = event_data['classes'].get(race_class_name, {})
                    stage_classes.add(race_class_name)
                else:
                    race_class = {}
                if race_class:
                    race_format = event_data['formats'].get(race_class.get('format', ''))
                else:
                    race_format = {}
                for race_result in heat_result['rounds']:
                    race_metrics = calculate_race_metrics(race_result, race_format)
                    race_result['metrics'] = race_metrics
                heat_result['metrics'] = aggregate_metrics([r['metrics'] for r in heat_result['rounds']], race_format)
            stage_result['metrics'] = {}
            stage_metrics = stage_result['metrics']
            for race_class in stage_classes:
                stage_metrics[race_class] = aggregate_metrics([h['metrics'] for h in stage_result['heats'].values() if h['class'] == race_class], race_format)
        event_result['metrics'] = {}
        event_metrics = event_result['metrics']
        for race_class in event_data['classes']:
            stage_metrics = [s['metrics'][race_class] for s in event_result['stages'].values() if race_class in s['metrics']]
            event_metrics[race_class] = aggregate_metrics(stage_metrics, race_format)
    return results


def calculate_race_metrics(race, race_format):
    laps = race['laps']
    if race_format.get('start', 'first-pass') == 'start-line':
        start_time = 0
    else:
        start_time = laps[0]['timestamp'] if laps else None
        laps = laps[1:]
    lap_count = len(laps)
    race_time = laps[-1]['timestamp'] - start_time if lap_count else 0
    lap_times = [laps[i]['timestamp'] - (laps[i-1]['timestamp'] if i-1 >= 0 else start_time) for i in range(len(laps))]
    metrics = {
        'lapCount': lap_count,
        'time': race_time,
        'lapTimes': lap_times,
        'fastest': np.min(lap_times) if lap_times else None,
        'mean': np.mean(lap_times) if lap_times else None,
        'stdDev': np.std(lap_times) if lap_times else None
    }
    if race_format['objective'] == RaceObjective.FASTEST_CONSECUTIVE:
        n = race_format['consecutiveLaps']
        metrics['fastest'+str(n)+'Consecutive'] = best_n_consecutive(lap_times, n)
    return metrics


def aggregate_metrics(metrics, race_format):
    lap_count = np.sum([r['lapCount'] for r in metrics])
    race_time = np.sum([r['time'] for r in metrics])
    lap_times = list(itertools.chain(*[r['lapTimes'] for r in metrics]))
    agg_metrics = {
        'lapCount': lap_count,
        'time': race_time,
        'lapTimes': lap_times,
        'fastest': np.min(lap_times) if lap_times else None,
        'mean': np.mean(lap_times) if lap_times else None,
        'stdDev': np.std(lap_times) if lap_times else None
    }
    if race_format['objective'] == RaceObjective.FASTEST_CONSECUTIVE:
        n = race_format['consecutiveLaps']
        metric_name = 'fastest' + str(n) + 'Consecutive'
        consecutive_totals = [np.sum(r[metric_name]) for r in metrics]
        if consecutive_totals:
            idx = np.argmin(consecutive_totals)
            agg_metrics[metric_name] = metrics[idx][metric_name]
    return agg_metrics


def best_n_consecutive(arr, n):
    consecutive_totals = [np.sum(arr[i:i+n]) for i in range(len(arr)+1-n)]
    if consecutive_totals:
        idx = np.argmin(consecutive_totals)
        return arr[idx:idx+n]
    else:
        return []


ID_PREFIX = 'id:'

def lookup_by_index_or_id(arr, key):
    if key.startswith(ID_PREFIX):
        entry_id = key[len(ID_PREFIX):]
        matching_entries = [e for e in arr if e['id'] == entry_id]
        return matching_entries[0] if matching_entries else []
    else:
        return arr[int(key)]


def calculate_leaderboard(results, event_data):
    event_name = event_data['name']
    for stage_idx, stage_info in enumerate(event_data['stages']):
        stage_id = ID_PREFIX + stage_info['id'] if 'id' in stage_info else stage_idx
        for heat_idx, heat_info in enumerate(stage_info['heats']):
            heat_id = ID_PREFIX + heat_info['id'] if 'id' in heat_info else heat_idx
            race_class_name = heat_info['class']
            race_class_info = event_data['classes'][race_class_name]
            race_format = event_data['formats'][race_class_info['format']]
            heat_psrs = []
            for pilot in heat_info['seats']:
                if pilot:
                    pilot_stages = results['pilots'][pilot]['events'][event_name]['stages']
                    if stage_id in pilot_stages:
                        pilot_heats = pilot_stages[stage_id]['heats']
                        if heat_id in pilot_heats:
                            metrics = pilot_heats[heat_id]['metrics']
                            heat_psrs.append(to_psr(pilot, metrics, race_format))
            heat_info['ranking'] = rank_psrs(heat_psrs)

        stage_psrs_by_class = {}
        for pilot, pilot_result in results['pilots'].items():
            pilot_stages = pilot_result['events'][event_name]['stages']
            if stage_id in pilot_stages:
                stage_metrics_by_class = pilot_stages[stage_id]['metrics']
                for race_class_name, metrics in stage_metrics_by_class.items():
                    race_class_info = event_data['classes'][race_class_name]
                    race_format = event_data['formats'][race_class_info['format']]
                    class_psrs = stage_psrs_by_class.get(race_class_name, None)
                    if not class_psrs:
                        class_psrs = []
                        stage_psrs_by_class[race_class_name] = class_psrs
                    class_psrs.append(to_psr(pilot, metrics, race_format))

        if not stage_info.get('leaderboards', None):
            # default if no leaderboard config is present
            stage_info['leaderboards'] = {race_class_name: {'method': LeaderboardMethod.BEST} for race_class_name in stage_psrs_by_class.keys()}
        stage_leaderboards = stage_info['leaderboards']

        race_classes_by_name = {}
        for race_class_name, race_class in event_data['classes'].items():
            race_classes_by_name[race_class_name] = race_class

        for parent_race_class_name, leaderboard in stage_leaderboards.items():
            method = leaderboard['method']
            if method == LeaderboardMethod.BEST:
                stage_psrs = []
                q = []
                q.append(parent_race_class_name)
                while q:
                    race_class_name = q.pop()
                    stage_psrs.extend(stage_psrs_by_class.get(race_class_name, []))
                    race_class = race_classes_by_name[race_class_name]
                    q.extend(race_class['children'].keys())
                leaderboard['ranking'] = rank_psrs(stage_psrs)
            else:
                raise ValueError("Unsupported method: " + method)
    return event_data


def to_psr(pilot, metrics, race_format):
    if race_format['objective'] == RaceObjective.MOST_LAPS_QUICKEST_TIME:
        score = (-metrics['lapCount'], metrics['time'])
        result = (metrics['lapCount'], metrics['time'])
    elif race_format['objective'] == RaceObjective.FASTEST_CONSECUTIVE:
        n = race_format['consecutiveLaps']
        metric_name = 'fastest' + str(n) + 'Consecutive'
        score = metrics[metric_name]
        result = score
    else:
        raise ValueError("Unsupported objective: " + race_format['objective'])
    return pilot, score, result


def rank_psrs(psrs):
    psrs.sort(key=lambda psr: psr[1])
    return list(map(lambda psr: {'pilot': psr[0], 'result': psr[2]}, psrs))


def export_leaderboard(RHData):
    msgs = export_results(RHData)
    results = pilot_results(msgs)
    event_data = export_event(RHData)
    results = calculate_metrics(results, event_data)
    leaderboard = calculate_leaderboard(results, event_data)
    return leaderboard
