import os
import unittest
import gevent
from datetime import datetime
from monotonic import monotonic
import json

os.environ['RH_CONFIG'] = 'config-dist.json'
TEST_DB = 'test-database.db'
if os.path.isfile(TEST_DB):
    os.remove(TEST_DB)
os.environ['RH_DATABASE'] = TEST_DB
os.environ['RH_INTERFACE'] = 'Mock'

from server import server, RHRace
import tests as tests_pkg

import logging

logger = logging.getLogger(__name__)


class ServerTest(unittest.TestCase):

    def setUp(self):
        logger.info('Starting test '+self._testMethodName)
        self.client = server.SOCKET_IO.test_client(server.APP)
        gevent.sleep(0.1)
        self.get_response('load_all')
        self.wait_for_response('heartbeat', 1)

    def tearDown(self):
        self.client.disconnect()

    @classmethod
    def setUpClass(cls):
        server.start()

    @classmethod
    def tearDownClass(cls):
        server.shutdown('Tear down')
        server.stop()

    def get_response(self, event):
        responses = self.client.get_received()
        for resp in reversed(responses):
            if resp['name'] == event:
                return resp['args'][0]
        self.fail('No response of type {0}'.format(event))

    def get_responses(self, *events):
        responses = self.client.get_received()
        evt_resps = filter(lambda resp: resp['name'] in events, responses)
        return [resp['args'][0] for resp in evt_resps]

    def wait_for_response(self, event, max_wait, filter_func=None):
        expiry_time = monotonic() + max_wait
        while monotonic() < expiry_time:
            responses = self.client.get_received()
            for resp in reversed(responses):
                if resp['name'] == event and (filter_func is None or filter_func(resp['args'][0])):
                    return resp['args'][0]
            gevent.sleep(0.1)
        self.fail('No response of type {0} within {1}secs'.format(event, max_wait))

    def test_node_data(self):
        resp = self.wait_for_response('node_data', 4)
        json.dumps(resp, allow_nan=False)
 
    def test_sensors(self):
        server.SENSORS.clear()

        # discovery
        server.SENSORS.discover(tests_pkg)
        self.assertEqual(len(server.SENSORS), 1)
        expected_name = 'TestSensor'
        self.assertEqual(server.SENSORS[0].name, expected_name)

        # environmental data
        server.rhconfig.SENSORS['test:/test'] = {
            'max_alarms': {
                'counter': 1
            }
        }
        server.emit_environmental_data()
        resp = self.get_response('environmental_data')
        self.assertEqual(resp[0][expected_name]['counter']['value'], 0)

        # alarms
        server.SENSORS[0].update()
        server.emit_environmental_data()
        resps = self.get_responses('environmental_data', 'priority_message')
        self.assertEqual(resps[0][0][expected_name]['counter']['value'], 1)
        self.assertEqual(resps[1]['key'], expected_name+' counter')

    def test_add_pilot(self):
        self.client.emit('load_data', {'load_types': ['pilot_data']})
        resp = self.get_response('pilot_data')
        num_pilots = len(resp['pilots'])
        self.client.emit('add_pilot')
        resp = self.get_response('pilot_data')
        self.assertEqual(len(resp['pilots']), num_pilots+1)
        last_pilot = resp['pilots'][-1]
        self.assertGreater(len(last_pilot['name']), 0)
        self.assertGreater(len(last_pilot['callsign']), 0)

    def test_add_pilot_init(self):
        self.client.emit('load_data', {'load_types': ['pilot_data']})
        resp = self.get_response('pilot_data')
        num_pilots = len(resp['pilots'])
        self.client.emit('add_pilot', {'name': 'foobar', 'callsign': 'Test new', 'team': 'Team T'})
        resp = self.get_response('pilot_data')
        self.assertEqual(len(resp['pilots']), num_pilots+1)
        pilots_by_id = sorted(resp['pilots'], key=lambda p: p['pilot_id'])
        last_pilot = pilots_by_id[-1]
        self.assertEqual(last_pilot['name'], 'foobar')
        self.assertEqual(last_pilot['callsign'], 'Test new')
        self.assertEqual(last_pilot['team'], 'Team T')

    def test_alter_pilot(self):
        for i in range(1, len(server.INTERFACE.nodes)):
            data = {
                'pilot_id': i,
                'callsign': 'Test '+str(i),
                'team_name': 'team T',
                'phonetic': 'Teeest',
                'name': 'Tester'
            }
            self.client.emit('alter_pilot', data)
            self.client.emit('load_data', {'load_types': ['pilot_data']})
            resp = self.get_response('pilot_data')
            for item in resp['pilots']:
                if item['pilot_id'] == i:
                    pilot = item
                    break
            self.assertEqual(pilot['callsign'], data['callsign'])
            self.assertEqual(pilot['phonetic'], data['phonetic'])
            self.assertEqual(pilot['name'], data['name'])

    def test_add_profile(self):
        self.client.emit('load_data', {'load_types': ['node_tuning']})
        resp = self.get_response('node_tuning')
        num_profiles = len(resp['profile_ids'])
        self.client.emit('add_profile')
        resp = self.get_response('node_tuning')
        self.assertEqual(len(resp['profile_ids']), num_profiles+1)

    def test_alter_profile(self):
        data = {
            'profile_name': 'Test ' + str(datetime.now()),
            'profile_description': 'Testing'
        }
        self.client.emit('alter_profile', data)
        resp = self.get_response('node_tuning')
        self.assertEqual(resp['profile_name'], data['profile_name'])
        self.assertEqual(resp['profile_description'], data['profile_description'])

    def test_add_race_format(self):
        self.client.emit('load_data', {'load_types': ['race_format']})
        resp = self.get_response('race_format')
        num_formats = len(resp['format_ids'])
        self.client.emit('add_race_format')
        resp = self.get_response('race_format')
        self.assertEqual(len(resp['format_ids']), num_formats+1)

    def test_alter_race_format(self):
        data = {
            'format_name': 'Test ' + str(datetime.now()),
            'race_mode': RHRace.RaceMode.FIXED_TIME,
            'race_time_sec': 33,
            'start_delay_min': 1,
            'start_delay_max': 4,
            'number_laps_win': 5,
            'win_condition': RHRace.WinCondition.FIRST_TO_LAP_X,
            'team_racing_mode': True
        }
        self.client.emit('alter_race_format', data)
        resp = self.get_response('race_format')
        self.assertEqual(resp['format_name'], data['format_name'])
        self.assertEqual(resp['race_mode'], data['race_mode'])
        self.assertEqual(resp['race_time_sec'], data['race_time_sec'])
        self.assertEqual(resp['start_delay_min'], data['start_delay_min'])
        self.assertEqual(resp['start_delay_max'], data['start_delay_max'])
        self.assertEqual(resp['number_laps_win'], data['number_laps_win'])
        self.assertEqual(resp['win_condition'], data['win_condition'])
        self.assertEqual(resp['team_racing_mode'], data['team_racing_mode'])

    def test_add_race_class(self):
        self.client.emit('load_data', {'load_types': ['class_data']})
        resp = self.get_response('class_data')
        num_classes = len(resp['classes'])
        self.client.emit('add_race_class')
        resp = self.get_response('class_data')
        self.assertEqual(len(resp['classes']), num_classes+1)

    def test_alter_race_class(self):
        data = {
            'id': 1,
            'name': 'New name',
            'format_id': 0,
            'description': 'Test class'
        }
        self.client.emit('alter_race_class', data)
        self.client.emit('load_data', {'load_types': ['class_data']})
        resp = self.get_response('class_data')
        self.assertEqual(resp['classes'][0]['name'], data['name'])
        self.assertEqual(resp['classes'][0]['format'], data['format_id'])
        self.assertEqual(resp['classes'][0]['description'], data['description'])

    def test_add_heat(self):
        self.client.emit('load_data', {'load_types': ['heat_data']})
        resp = self.get_response('heat_data')
        num_heats = len(resp['heats'])
        self.client.emit('add_heat')
        resp = self.get_response('heat_data')
        self.assertEqual(len(resp['heats']), num_heats+1)

    def test_alter_heat(self):
        data = {
            'heat': 1,
            'node': 0,
            'pilot': 1,
            'note': 'Test',
            'class': 1
        }
        self.client.emit('alter_heat', data)
        self.client.emit('load_data', {'load_types': ['heat_data']})
        resp = self.get_response('heat_data')
        self.assertEqual(resp['heats'][1]['pilots'][0], data['pilot'])
        self.assertEqual(resp['heats'][1]['note'], data['note'])
        self.assertEqual(resp['heats'][1]['class_id'], data['class'])

    def test_run_a_race(self):
        self.client.emit('alter_heat', {'heat':1, 'node':0, 'pilot':1})
        self.client.emit('set_race_format', {'race_format': 5})
        self.client.emit('stage_race')
        self.get_response('stage_ready')
        resp = self.wait_for_response('race_status', 1)
        self.assertEquals(resp['race_status'], RHRace.RaceStatus.RACING)
        server.INTERFACE.simulate_lap(0)
        resp = self.wait_for_response('pass_record', 1)
        self.assertEqual(resp['node'], 0)
        self.client.emit('stop_race')


# scanner

    def test_scanner(self):
        self.client.emit('set_frequency', {
            'node': 0,
            'frequency': 5888
        })
        is_freq_set = lambda f: lambda d:d['frequency'][0] == f
        self.wait_for_response('heartbeat', 1, is_freq_set(5888))

        self.client.emit('set_scan', {
            'node': 0,
            'scan': True,
        })
        # allow some scanning to happen
        gevent.sleep(1)
        resp = self.wait_for_response('scan_data', 1)
        num_freqs = len(resp['frequency'])
        self.assertGreater(num_freqs, 0)
        self.assertEqual(len(resp['rssi']), num_freqs)

        self.client.emit('set_scan', {
            'node': 0,
            'scan': False,
        })
        # check original frequency is restored
        resp = self.wait_for_response('heartbeat', 1, is_freq_set(5888))

# verify LiveTime compatibility

    def test_livetime_get_version(self):
        resp = self.client.emit('get_version', callback=True)
        self.assertIn('major', resp)
        self.assertIn('minor', resp)

    def test_livetime_get_timestamp(self):
        resp = self.client.emit('get_timestamp', callback=True)
        self.assertIn('timestamp', resp)

    def test_livetime_get_settings(self):
        resp = self.client.emit('get_settings', callback=True)
        self.assertIn('nodes', resp)
        for n in resp['nodes']:
            self.assertTrue('frequency' in n)
            self.assertTrue('trigger_rssi' in n)

    def test_livetime_set_calibration_threshold(self):
        self.client.emit('set_calibration_threshold', {
            'calibration_threshold': 0
        })

    def test_livetime_set_calibration_offset(self):
        self.client.emit('set_calibration_offset', {
            'calibration_offset': 0
        })

    def test_livetime_set_trigger_threshold(self):
        self.client.emit('set_trigger_threshold', {
            'trigger_threshold': 0
        })

    def test_livetime_set_frequency(self):
        data = {
            'node': 0,
            'frequency': 5800
        }
        # trigger livetime client mode
        self.client.emit('get_version')
        self.client.emit('set_frequency', data)

        is_same_node = lambda d: d['node'] == 0
        resp = self.wait_for_response('frequency_set', 0.1, is_same_node)
        self.assertEqual(resp, data)

    def test_livetime_reset_auto_calibration(self):
        self.client.emit('reset_auto_calibration', {
            'node': -1
        })
        self.client.emit('stop_race')

    def test_livetime_heartbeat(self):
        # trigger livetime client mode
        self.client.emit('get_version')
        resp = self.wait_for_response('heartbeat', 1)
        self.assertIn('current_rssi', resp)
        self.assertTrue(len(resp['current_rssi']) > 0)

    def test_livetime_pass_record(self):
        # trigger livetime client mode
        self.client.emit('get_version')
        server.RACE.race_status = 1
        node = server.INTERFACE.nodes[0]
        server.RACE.start_time_monotonic = 10
        server.RACE.start_time_epoch_ms = server.PROGRAM_START.monotonic_to_epoch_millis(server.RACE.start_time_monotonic)
        server.pass_record_callback(node, 19.8, 0)
        resp = self.wait_for_response('pass_record', 1)
        self.assertIn('node', resp)
        self.assertIn('frequency', resp)
        self.assertIn('timestamp', resp)
        self.assertEqual(resp['timestamp'], server.PROGRAM_START.monotonic_to_epoch_millis(server.RACE.start_time_monotonic) + 19800)


if __name__ == '__main__':
    unittest.main()
