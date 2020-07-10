'''python -m unittest discover'''
import os
import sys
import unittest
import socketio
import gevent
from datetime import datetime

sys.path.append('../server')
sys.path.append('../interface')

os.environ['RH_INTERFACE'] = 'Mock'

import server
from Node import Node

class ServerTest(unittest.TestCase):
    def setUp(self):
        self.client = server.SOCKET_IO.test_client(server.APP)

    def tearDown(self):
        self.client.disconnect()

    def get_response(self, event):
        responses = self.client.get_received()
        for resp in reversed(responses):
            if resp['name'] == event:
                return resp['args'][0]
        self.fail('No response of type {0}'.format(event))

    def test_add_pilot(self):
        self.client.emit('load_data', {'load_types': ['pilot_data']})
        resp = self.get_response('pilot_data')
        num_pilots = len(resp['pilots'])
        self.client.emit('add_pilot')
        resp = self.get_response('pilot_data')
        self.assertEquals(len(resp['pilots']), num_pilots+1)

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
            self.assertEquals(pilot['callsign'], data['callsign'])
            self.assertEquals(pilot['phonetic'], data['phonetic'])
            self.assertEquals(pilot['name'], data['name'])

    def test_add_profile(self):
        self.client.emit('load_data', {'load_types': ['node_tuning']})
        resp = self.get_response('node_tuning')
        num_profiles = len(resp['profile_ids'])
        self.client.emit('add_profile')
        resp = self.get_response('node_tuning')
        self.assertEquals(len(resp['profile_ids']), num_profiles+1)

    def test_alter_profile(self):
        data = {
            'profile_name': 'Test ' + str(datetime.now()),
            'profile_description': 'Testing'
        }
        self.client.emit('alter_profile', data)
        resp = self.get_response('node_tuning')
        self.assertEquals(resp['profile_name'], data['profile_name'])
        self.assertEquals(resp['profile_description'], data['profile_description'])

    def test_add_race_format(self):
        self.client.emit('load_data', {'load_types': ['race_format']})
        resp = self.get_response('race_format')
        num_formats = len(resp['format_ids'])
        self.client.emit('add_race_format')
        resp = self.get_response('race_format')
        self.assertEquals(len(resp['format_ids']), num_formats+1)

    def test_alter_race_format(self):
        data = {
            'format_name': 'Test ' + str(datetime.now()),
            'race_mode': 0,
            'race_time': 30,
            'start_delay_min': 1,
            'start_delay_max': 4,
            'number_laps_win': 5,
            'win_condition': 0,
            'team_racing_mode': True
        }
        self.client.emit('alter_race_format', data)
        resp = self.get_response('race_format')
        self.assertEquals(resp['format_name'], data['format_name'])
        self.assertEquals(resp['race_mode'], data['race_mode'])
        self.assertEquals(resp['race_time_sec'], data['race_time'])
        self.assertEquals(resp['start_delay_min'], data['start_delay_min'])
        self.assertEquals(resp['start_delay_max'], data['start_delay_max'])
        self.assertEquals(resp['number_laps_win'], data['number_laps_win'])
        self.assertEquals(resp['win_condition'], data['win_condition'])
        self.assertEquals(resp['team_racing_mode'], data['team_racing_mode'])

    def test_add_race_class(self):
        self.client.emit('load_data', {'load_types': ['class_data']})
        resp = self.get_response('class_data')
        num_classes = len(resp['classes'])
        self.client.emit('add_race_class')
        resp = self.get_response('class_data')
        self.assertEquals(len(resp['classes']), num_classes+1)

    def test_alter_race_class(self):
        data = {
            'class_id': 1,
            'class_name': 'New name',
            'class_format': 0,
            'class_description': 'Test class'
        }
        self.client.emit('alter_race_class', data)
        self.client.emit('load_data', {'load_types': ['class_data']})
        resp = self.get_response('class_data')
        self.assertEquals(resp['classes'][0]['name'], data['class_name'])
        self.assertEquals(resp['classes'][0]['format'], data['class_format'])
        self.assertEquals(resp['classes'][0]['description'], data['class_description'])

    def test_add_heat(self):
        self.client.emit('load_data', {'load_types': ['heat_data']})
        resp = self.get_response('heat_data')
        num_heats = len(resp['heats'])
        self.client.emit('add_heat')
        resp = self.get_response('heat_data')
        self.assertEquals(len(resp['heats']), num_heats+1)

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
        self.assertEquals(resp['heats'][1]['pilots'][0], data['pilot'])
        self.assertEquals(resp['heats'][1]['note'], data['note'])
        self.assertEquals(resp['heats'][1]['class_id'], data['class'])

# scanner

    def test_scanner(self):
        self.client.emit('set_frequency', {
            'node': 0,
            'frequency': 5888
        })
        self.client.emit('set_scan', {
            'node': 0,
            'min_scan_frequency': 5645,
            'max_scan_frequency': 5945,
            'max_scan_interval': 1,
            'min_scan_interval': 1,
            'scan_zoom': 1,
        })
        # allow some scanning to happen
        new_freq = 5888
        while new_freq == 5888:
            gevent.sleep(0.5)
            resp = self.get_response('heartbeat')
            new_freq = resp['frequency'][0]

        self.client.emit('set_scan', {
            'node': 0,
            'min_scan_frequency': 0,
            'max_scan_frequency': 0,
            'max_scan_interval': 0,
            'min_scan_interval': 0,
            'scan_zoom': 0,
        })
        # check original frequency is restored
        gevent.sleep(0.5)
        resp = self.get_response('heartbeat')
        gevent.sleep(0.25)
        resp = self.get_response('heartbeat')
        self.assertEqual(resp['frequency'][0], 5888)

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
        self.client.get_received() # clear received buffer
        data = {
            'node': 0,
            'frequency': 5800
        }
        # trigger livetime client mode
        self.client.emit('get_version')
        self.client.emit('set_frequency', data)

        responses = self.client.get_received()
        for resp in responses:
            if resp['name'] == 'frequency_set':
                if resp['args'][0]['node'] == 0:
                    self.assertEquals(resp['args'][0], data)
                    return

        self.fail('No valid responses')

    def test_livetime_reset_auto_calibration(self):
        self.client.emit('reset_auto_calibration', {
            'node': -1
        })

    def test_livetime_heartbeat(self):
        # trigger livetime client mode
        self.client.emit('get_version')
        gevent.sleep(0.5)
        resp = self.get_response('heartbeat')
        self.assertIn('current_rssi', resp)
        self.assertTrue(len(resp['current_rssi']) > 0)

    def test_livetime_pass_record(self):
        # trigger livetime client mode
        self.client.emit('get_version')
        server.RACE.race_status = 1
        node = Node()
        node.index = 0
        server.pass_record_callback(node, server.RACE.start_time_monotonic + 19.8, 0)
        resp = self.get_response('pass_record')
        self.assertIn('node', resp)
        self.assertIn('frequency', resp)
        self.assertIn('timestamp', resp)
        self.assertEqual(resp['timestamp'], server.monotonic_to_milliseconds(server.RACE.start_time_monotonic) + 19800)

if __name__ == '__main__':
    unittest.main()
