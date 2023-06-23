'''python -m unittest discover'''
import os
import sys
import unittest
import gevent
from datetime import datetime

sys.path.append('../server')
sys.path.append('../server/util')
sys.path.append('../server/plugins')
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

    def test_sensors(self):
        self.assertTrue(any(s.name == 'TestSensor' for s in server.RaceContext.sensors))

    def test_add_pilot(self):
        self.client.emit('load_data', {'load_types': ['pilot_data']})
        resp = self.get_response('pilot_data')
        num_pilots = len(resp['pilots'])
        self.client.emit('add_pilot')
        resp = self.get_response('pilot_data')
        self.assertEqual(len(resp['pilots']), num_pilots+1)

    def test_alter_pilot(self):
        for i in range(1, len(server.RaceContext.interface.nodes)):
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

    def test_delete_pilot(self):
        self.client.emit('load_data', {'load_types': ['pilot_data']})
        resp = self.get_response('pilot_data')
        num_pilots = len(resp['pilots'])
        pilot_id = 0
        for pilot in resp['pilots']:
            pilot_id = pilot['pilot_id']
        self.client.emit('delete_pilot', {'pilot': pilot_id})
        self.client.emit('load_data', {'load_types': ['pilot_data']})
        resp = self.get_response('pilot_data')
        self.assertEqual(len(resp['pilots']), num_pilots-1)

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

    def test_delete_profile(self):
        self.client.emit('load_data', {'load_types': ['node_tuning']})
        resp = self.get_response('node_tuning')
        num_profiles = len(resp['profile_ids'])
        profile_id = 0
        for profile in resp['profile_ids']:
            profile_id = profile
        self.client.emit('set_profile', {'profile': profile_id})
        self.client.emit('delete_profile')
        self.client.emit('load_data', {'load_types': ['node_tuning']})
        resp = self.get_response('node_tuning')
        self.assertEqual(len(resp['profile_ids']), num_profiles-1)

    def test_add_race_format(self):
        self.client.emit('load_data', {'load_types': ['format_data']})
        resp = self.get_response('format_data')
        num_formats = len(resp['formats'])
        self.client.emit('add_race_format', {'source_format_id': 1})
        resp = self.get_response('format_data')
        self.assertEqual(len(resp['formats']), num_formats+1)

    def test_alter_race_format(self):
        data = {
            'format_id': 10,
            'format_name': 'Test ' + str(datetime.now()),
            'race_mode': 0,
            'race_time_sec': 30,
            'start_delay_min_ms': 1000,
            'start_delay_max_ms': 4000,
            'number_laps_win': 5,
            'win_condition': 0,
            'team_racing_mode': True
        }
        self.client.emit('alter_race_format', data)
        resp = self.get_response('format_data')
        fmts_list = resp['formats']
        for resp in fmts_list:
            if resp['id'] == data['format_id']:
                self.assertEqual(resp['name'], data['format_name'])
                self.assertEqual(resp['race_mode'], data['race_mode'])
                self.assertEqual(resp['race_time_sec'], data['race_time_sec'])
                self.assertEqual(resp['start_delay_min'], data['start_delay_min_ms'])
                self.assertEqual(resp['start_delay_max'], data['start_delay_max_ms'])
                self.assertEqual(resp['number_laps_win'], data['number_laps_win'])
                self.assertEqual(resp['win_condition'], data['win_condition'])
                self.assertEqual(resp['team_racing_mode'], data['team_racing_mode'])
                return
        self.fail('No matching format in response')

    def test_delete_race_format(self):
        self.client.emit('load_data', {'load_types': ['format_data']})
        resp = self.get_response('format_data')
        num_formats = len(resp['formats'])
        format_id = 0
        for format_obj in resp['formats']:
            format_id = format_obj['id']
        self.client.emit('delete_race_format', {'format_id': format_id})
        resp = self.get_response('format_data')
        self.assertEqual(len(resp['formats']), num_formats-1)

    def test_add_race_class(self):
        self.client.emit('load_data', {'load_types': ['class_data']})
        resp = self.get_response('class_data')
        num_classes = len(resp['classes'])
        self.client.emit('add_race_class')
        resp = self.get_response('class_data')
        self.assertEqual(len(resp['classes']), num_classes+1)

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
        self.assertEqual(resp['classes'][0]['name'], data['class_name'])
        self.assertEqual(resp['classes'][0]['format'], data['class_format'])
        self.assertEqual(resp['classes'][0]['description'], data['class_description'])

    def test_delete_race_class(self):
        self.client.emit('load_data', {'load_types': ['class_data']})
        resp = self.get_response('class_data')
        num_classes = len(resp['classes'])
        class_id = 0
        for class_obj in resp['classes']:
            class_id = class_obj['id']
        self.client.emit('delete_class', {'class': class_id})
        resp = self.get_response('class_data')
        self.assertEqual(len(resp['classes']), num_classes-1)

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
            'class': 1,
            'slot_id': 1
        }
        self.client.emit('alter_heat', data)
        self.client.emit('load_data', {'load_types': ['heat_data']})
        resp = self.get_response('heat_data')
        self.assertEqual(resp['heats'][0]['slots'][0]['pilot_id'], data['pilot'])
        self.assertEqual(resp['heats'][0]['note'], data['note'])
        self.assertEqual(resp['heats'][0]['class_id'], data['class'])

    def test_delete_heat(self):
        self.client.emit('load_data', {'load_types': ['heat_data']})
        resp = self.get_response('heat_data')
        num_heats = len(resp['heats'])
        heat_id = 0
        for heat in resp['heats']:
            heat_id = heat['id']
        self.client.emit('delete_heat', {'heat': heat_id})
        resp = self.get_response('heat_data')
        self.assertEqual(len(resp['heats']), num_heats-1)

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
                    self.assertEqual(resp['args'][0], data)
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
        server.RaceContext.race.race_status = 1
        node = Node()
        node.index = 0
        server.RaceContext.race.start_time_monotonic = 10
        server.RaceContext.race.start_time_epoch_ms = server.monotonic_to_epoch_millis(server.RaceContext.race.start_time_monotonic)
        server.pass_record_callback(node, 19.8+server.RaceContext.race.start_time_monotonic, 0)
        gevent.sleep(0.1)
        resp = self.get_response('pass_record')
        self.assertIn('node', resp)
        self.assertIn('frequency', resp)
        self.assertIn('timestamp', resp)
        self.assertEqual(resp['timestamp'], server.monotonic_to_epoch_millis(server.RaceContext.race.start_time_monotonic) + 19800)

# RHAPI

    def test_database_api(self):
        self.client.emit('load_data', {'load_types': ['pilot_data']})
        ld_pilots = self.get_response('pilot_data')['pilots']
        db_pilots = server.RHAPI.db.pilots
        num_pilots = len(server.RHAPI.db.pilots)
        self.assertGreater(num_pilots, 7)
        num_matched = 0
        for ld_pilot in ld_pilots:
            for db_pilot in db_pilots:
                if ld_pilot['pilot_id'] == db_pilot.id and ld_pilot['callsign'] == db_pilot.callsign and \
                            ld_pilot['phonetic'] == db_pilot.phonetic and ld_pilot['name'] == db_pilot.name and \
                            ld_pilot['team'] == db_pilot.team and ld_pilot['color'] == db_pilot.color and \
                            ld_pilot['active'] == db_pilot.active:
                    num_matched += 1
        self.assertGreater(num_matched, 7)
        self.assertEqual(len(ld_pilots), len(db_pilots))
        self.assertEqual(num_matched, len(db_pilots))
        num_matched = 0
        for ld_pilot in ld_pilots:
            db_pilot = server.RHAPI.db.pilot_by_id(ld_pilot['pilot_id'])
            self.assertNotEqual(db_pilot, None)
            db_pilot_match = (ld_pilot['pilot_id'] == db_pilot.id and ld_pilot['callsign'] == db_pilot.callsign and \
                              ld_pilot['phonetic'] == db_pilot.phonetic and ld_pilot['name'] == db_pilot.name and \
                              ld_pilot['team'] == db_pilot.team and ld_pilot['color'] == db_pilot.color and \
                              ld_pilot['active'] == db_pilot.active)
            self.assertEqual(db_pilot_match, True)
            if db_pilot_match:
                num_matched += 1
        self.assertGreater(num_matched, 7)
        ld_pilot['name'] = 'Test Name'
        ld_pilot['callsign'] = 'testcallsign'
        ld_pilot['phonetic'] ='test phonetic'
        ld_pilot['team'] = 'T'
        ld_pilot['color'] = 'Red'
        new_pilot = server.RHAPI.db.pilot_add(ld_pilot['name'], ld_pilot['callsign'], \
                                              ld_pilot['phonetic'], ld_pilot['team'], ld_pilot['color'])
        self.assertNotEqual(new_pilot, None)
        self.assertEqual(len(server.RHAPI.db.pilots), num_pilots+1)
        db_pilot = server.RHAPI.db.pilot_by_id(new_pilot.id)
        self.assertNotEqual(db_pilot, None)
        db_pilot_match = (ld_pilot['callsign'] == db_pilot.callsign and \
                          ld_pilot['phonetic'] == db_pilot.phonetic and ld_pilot['name'] == db_pilot.name and \
                          ld_pilot['team'] == db_pilot.team and ld_pilot['color'] == db_pilot.color)
        self.assertEqual(db_pilot_match, True)
        ld_pilot['name'] = 'Test Name 2'
        ld_pilot['callsign'] = 'testcallsign2'
        ld_pilot['phonetic'] ='test phonetic 2'
        ld_pilot['team'] = 'G'
        ld_pilot['color'] = 'Green'
        new_pilot2, race_list = server.RHAPI.db.pilot_alter(new_pilot.id, ld_pilot['name'], ld_pilot['callsign'], \
                                                            ld_pilot['phonetic'], ld_pilot['team'], ld_pilot['color'])
        self.assertNotEqual(new_pilot2, None)
        self.assertNotEqual(race_list, None)
        db_pilot = server.RHAPI.db.pilot_by_id(new_pilot.id)
        self.assertNotEqual(db_pilot, None)
        self.assertEqual(db_pilot.id, new_pilot2.id)
        db_pilot_match = (ld_pilot['callsign'] == db_pilot.callsign and \
                          ld_pilot['phonetic'] == db_pilot.phonetic and ld_pilot['name'] == db_pilot.name and \
                          ld_pilot['team'] == db_pilot.team and ld_pilot['color'] == db_pilot.color)
        self.assertEqual(db_pilot_match, True)
        result_flag = server.RHAPI.db.pilot_delete(new_pilot.id)
        self.assertEqual(result_flag, True)
        self.assertEqual(len(server.RHAPI.db.pilots), num_pilots)       

    def test_sensors_api(self):
        self.assertGreaterEqual(len(server.RHAPI.sensors.sensors_dict), 0)
        self.assertEqual(server.RHAPI.sensors.sensor_names[0], 'TestSensor')
        self.assertGreaterEqual(len(server.RHAPI.sensors.sensor_objs), 0)
        sensor = server.RHAPI.sensors.sensor_obj(server.RHAPI.sensors.sensor_names[0])
        self.assertEqual(sensor.getName(), server.RHAPI.sensors.sensor_names[0])
        self.assertEqual(sensor.getAddress(), 123)
        readings = sensor.getReadings()
        count = readings['counter']['value']
        sensor.update()
        readings = sensor.getReadings()
        self.assertEqual(readings['counter']['value'], count+1)

        
if __name__ == '__main__':
    unittest.main()
