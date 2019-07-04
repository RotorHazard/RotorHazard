'''python -m unittest discover'''
import sys
import unittest
import socketio

sys.path.append('../server')

import server

class ServerTest(unittest.TestCase):
    def setUp(self):
        self.client = server.SOCKET_IO.test_client(server.APP)

    def get_response(self, event):
        responses = self.client.get_received()
        for resp in responses:
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
        for i in range(1, 9):
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
	        self.assertEquals(resp['pilots'][i-1]['callsign'], data['callsign'])
	        self.assertEquals(resp['pilots'][i-1]['phonetic'], data['phonetic'])
	        self.assertEquals(resp['pilots'][i-1]['name'], data['name'])

    def test_add_profile(self):
        self.client.emit('load_data', {'load_types': ['node_tuning']})
        resp = self.get_response('node_tuning')
        num_profiles = len(resp['profile_ids'])
        self.client.emit('add_profile')
        resp = self.get_response('node_tuning')
        self.assertEquals(len(resp['profile_ids']), num_profiles+1)

    def test_alter_profile(self):
        data = {
        	'profile_name': 'Test',
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
        	'format_name': 'Test',
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

    def test_race(self):
        self.client.emit('stage_race')
        self.client.emit('stop_race')
        self.client.emit('load_data', {'load_types': ['round_data']})
        resp = self.get_response('round_data')
