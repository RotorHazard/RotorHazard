import unittest
import json
import server.race_explorer_core as racex
import server.heat_generator_endpoints as heatgen


class BracketsTest(unittest.TestCase):

    DEBUG = False

    def test_brackets(self):
        with open('tests/test_converted_ifpv_event.json') as f:
            event_data = json.loads(f.read())

        event_data['formats'] = {'BDRA Qualifying': {'objective': 'most-laps-quickest-time'}}
        event_name = event_data['name']
        results = {'pilots': {pilot: {'events': {event_name: {'stages': {}}}} for pilot in event_data['pilots']}}

        stage_idx = 0
        race_class_name = 'BDRA Open'
        event_data['stages'][stage_idx]['leaderboards'] = {race_class_name: {'method': 'best'}}

        results_class = race_class_name
        mains_class = race_class_name
        n_seats = 4

        for bracket in range(1,7):
            self.generate_heat_results(event_data, event_name, stage_idx, results)
            self.debugJson('test-stage-{}-generated-results.json'.format(stage_idx), results)
            results = racex.calculate_metrics(results, event_data)
            self.debugJson('test-stage-{}-metrics.json'.format(stage_idx), results)
            leaderboards = racex.calculate_leaderboard(results, event_data)
            self.debugJson('test-stage-{}-leaderboards.json'.format(stage_idx), leaderboards)
            # prep next stage
            bracket_name = 'Bracket '+str(bracket)
            event_data['stages'].append({'name': bracket_name, 'heats': []})
            stage_idx = len(event_data['stages']) - 1
            bracket_data = heatgen.mgp_brackets(leaderboards, stage_idx, results_class, mains_class, n_seats, bracket)
            self.assertGreater(len(bracket_data['heats']), 0, bracket_name)
            event_data['stages'][stage_idx].update(bracket_data)
            self.debugJson('test-stage-{}-bracket-{}.json'.format(stage_idx, bracket), event_data)

        self.generate_heat_results(event_data, event_name, stage_idx, results)
        self.debugJson('test-stage-{}-generated-results.json'.format(stage_idx), results)
        results = racex.calculate_metrics(results, event_data)
        self.debugJson('test-stage-{}-metrics.json'.format(stage_idx), results)
        leaderboards = racex.calculate_leaderboard(results, event_data)
        self.debugJson('test-stage-{}-leaderboards.json'.format(stage_idx), leaderboards)

        actual_positions = list(map(lambda e: e['pilot'], leaderboards['stages'][stage_idx]['leaderboards'][mains_class]['ranking']))
        expected_positions = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6',
                              'P9', 'P10', 'P7', 'P8', 'P11', 'P12',
                              'P13', 'P14', 'P15', 'P16'
        ]
        self.assertListEqual(actual_positions, expected_positions)

    def generate_heat_results(self, event_data, event_name, stage_idx, results):
        max_laps = 17
        for heat_idx, heat in enumerate(event_data['stages'][stage_idx]['heats']):
            for seat in heat['seats']:
                laps_to_assign = max_laps - int(seat[1:])
                lap_time = 1/laps_to_assign
                laps = []
                for i in range(laps_to_assign):
                    laps.append({'timestamp': i*lap_time, 'lap': i, 'location': 0})
                round_results = {'laps': laps}
                heat_results = {'rounds': [round_results]}
                stage_results = {'heats': {heat_idx: heat_results}}
                event_results = results['pilots'][seat]['events'][event_name]
                event_results['stages'][stage_idx] = stage_results
                results['pilots'][seat]['events'][event_name] = event_results

    def debugJson(self, filename, data):
        if BracketsTest.DEBUG:
            with open(filename, 'wt') as f:
                f.write(json.dumps(data, default=racex.json_numpy_converter))


if __name__ == '__main__':
    unittest.main()
