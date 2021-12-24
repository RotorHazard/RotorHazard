import unittest
import json
import server.race_explorer_endpoints as racex

class RaceExplorerTest(unittest.TestCase):
    def test_pilot_results(self):
        with open('tests/test_result_msgs.json') as f:
            msgs = json.loads(f.read())['messages']
        results = racex.pilot_results(msgs)
        # compensate for numeric indices to json property strings
        actual = json.loads(json.dumps(results))
        with open('tests/test_results.json') as f:
            expected = json.loads(f.read())
        self.assertDictEqual(actual, expected)


    def test_calculate_metrics(self):
        with open('tests/test_results.json') as f:
            results = json.loads(f.read())
        with open('tests/test_results_event.json') as f:
            event_data = json.loads(f.read())
        actual = racex.calculate_metrics(results, event_data)
        with open('tests/test_results_metrics.json') as f:
            expected = json.loads(f.read())
        self.maxDiff=None
        self.assertDictEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
