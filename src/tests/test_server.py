'''python -m unittest discover'''
import os
import sys
import unittest
import gevent
from datetime import datetime
from flask.blueprints import Blueprint

sys.path.append('../server')
sys.path.append('../server/util')
sys.path.append('../server/plugins')
sys.path.append('../interface')

os.environ['RH_INTERFACE'] = 'Mock'

import server
from Node import Node
from RHUI import UIField, UIFieldType

class ServerTest(unittest.TestCase):
    def setUp(self):
        self.client = server.SOCKET_IO.test_client(server.APP)
        server.rh_program_initialize(reg_endpoints_flag=False)

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
        for pilot in server.RaceContext.rhdata.get_pilots():
            data = {
                'pilot_id': pilot.id,
                'callsign': 'Test '+str(pilot.id),
                'team_name': 'team T',
                'phonetic': 'Teeest',
                'name': 'Tester'
            }
            self.client.emit('alter_pilot', data)
            self.client.emit('load_data', {'load_types': ['pilot_data']})
            resp = self.get_response('pilot_data')
            for item in resp['pilots']:
                if item['pilot_id'] == pilot.id:
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
            'unlimited_time': 0,
            'race_time_sec': 30,
            'start_delay_min_ms': 1000,
            'start_delay_max_ms': 4000,
            'number_laps_win': 5,
            'win_condition': 0,
            'team_racing_mode': 1
        }
        self.client.emit('alter_race_format', data)
        resp = self.get_response('format_data')
        fmts_list = resp['formats']
        for resp in fmts_list:
            if resp['id'] == data['format_id']:
                self.assertEqual(resp['name'], data['format_name'])
                self.assertEqual(resp['unlimited_time'], data['unlimited_time'])
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
            'name': 'Test',
            'class': 1,
            'slot_id': 1
        }
        self.client.emit('alter_heat', data)
        self.client.emit('load_data', {'load_types': ['heat_data']})
        resp = self.get_response('heat_data')
        self.assertEqual(resp['heats'][0]['slots'][0]['pilot_id'], data['pilot'])
        self.assertEqual(resp['heats'][0]['name'], data['name'])
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

# trackside compatibility

    def test_trackside_get_pi_time(self):
        resp = self.client.emit('get_server_time', callback=True)
        self.assertIn('server_time_s', resp)
        resp['server_time_s']

    def test_trackside_stage_race(self):
        resp = self.client.emit('get_server_time', callback=True)
        server_ts = resp['server_time_s']

        resp = self.client.emit('ts_race_stage', {'start_time_s': server_ts + 2})

    def test_trackside_stop_race(self):
        resp = self.client.emit('ts_race_stop')

# RHAPI

    def test_api_root(self):
        self.assertEqual(server.RHAPI.API_VERSION_MAJOR, 1)
        self.assertEqual(server.RHAPI.API_VERSION_MINOR, 3)
        self.assertEqual(server.RHAPI.__, server.RHAPI.language.__)

    def test_ui_api(self):
        panels = server.RHAPI.ui.register_panel('test_panel', "Test Panel", 'test_page', 1)
        self.assertEqual(panels, server.RHAPI.ui.panels)
        self.assertGreater(len(server.RHAPI.ui.panels), 0)
        panel = server.RHAPI.ui.panels[0]
        panel_match = (panel.name == 'test_panel' and \
                       panel.label == "Test Panel" and \
                       panel.page == 'test_page' and \
                       panel.order == 1)
        self.assertEqual(panel_match, True)

        buttons = server.RHAPI.ui.register_quickbutton('test_panel', 'test_button', "Test Button", server.RHAPI.ui.register_quickbutton)
        button = buttons[0]
        button_match = (button.panel == 'test_panel' and \
                        button.name == 'test_button' and \
                        button.label == "Test Button" and \
                        button.fn == server.RHAPI.ui.register_quickbutton)  #pylint: disable=comparison-with-callable
        self.assertEqual(button_match, True)

        bp = Blueprint('test', __name__)
        @bp.route('/bptest')
        def bp_test_page():
            return "test page content"
        server.RHAPI.ui.blueprint_add(bp)
        with server.APP.test_client() as tc:
            resp = tc.get('/bptest')
        self.assertEqual(resp.status_code, 200)

        server.RHAPI.ui.message_speak("Test Speak")
        resp = self.get_response('phonetic_text')
        self.assertEqual(resp['text'], "Test Speak")
        self.assertEqual(resp['domain'], False)
        self.assertEqual(resp['winner_flag'], False)

        server.RHAPI.ui.message_notify("Test Interrupt")
        resp = self.get_response('priority_message')
        self.assertEqual(resp['message'], "Test Interrupt")
        self.assertEqual(resp['interrupt'], False)

        server.RHAPI.ui.message_alert("Test Alert")
        resp = self.get_response('priority_message')
        self.assertEqual(resp['message'], "Test Alert")
        self.assertEqual(resp['interrupt'], True)

    def test_fields_api(self):
        server.RHAPI.fields.register_option(UIField('test_option', 'Test Option', UIFieldType.TEXT), 'test_panel', 1)
        option = server.RHAPI.fields.options[0]
        opt_match = (option.name == 'test_option' and \
                     option.field.label == "Test Option" and \
                     option.field.field_type == UIFieldType.TEXT and \
                     option.panel == 'test_panel' and \
                     option.order == 1)
        self.assertEqual(opt_match, True)

        server.RHAPI.fields.register_pilot_attribute(UIField('test_attribute', 'Test Attribute', UIFieldType.TEXT))
        attr = server.RHAPI.fields.pilot_attributes[0]
        attr_match = (attr.name == 'test_attribute'  and \
                      attr.label == "Test Attribute" and \
                      attr.field_type == UIFieldType.TEXT)
        self.assertEqual(attr_match, True)

        server.RHAPI.fields.register_heat_attribute(UIField('test_attribute', 'Test Attribute', UIFieldType.TEXT))
        attr = server.RHAPI.fields.heat_attributes[0]
        attr_match = (attr.name == 'test_attribute'  and \
                      attr.label == "Test Attribute" and \
                      attr.field_type == UIFieldType.TEXT)
        self.assertEqual(attr_match, True)

        server.RHAPI.fields.register_raceclass_attribute(UIField('test_attribute', 'Test Attribute', UIFieldType.TEXT))
        attr = server.RHAPI.fields.raceclass_attributes[0]
        attr_match = (attr.name == 'test_attribute'  and \
                      attr.label == "Test Attribute" and \
                      attr.field_type == UIFieldType.TEXT)
        self.assertEqual(attr_match, True)

        server.RHAPI.fields.register_race_attribute(UIField('test_attribute', 'Test Attribute', UIFieldType.TEXT))
        attr = server.RHAPI.fields.race_attributes[0]
        attr_match = (attr.name == 'test_attribute'  and \
                      attr.label == "Test Attribute" and \
                      attr.field_type == UIFieldType.TEXT)
        self.assertEqual(attr_match, True)

        server.RHAPI.fields.register_raceformat_attribute(UIField('test_attribute', 'Test Attribute', UIFieldType.TEXT))
        attr = server.RHAPI.fields.race_attributes[0]
        attr_match = (attr.name == 'test_attribute'  and \
                      attr.label == "Test Attribute" and \
                      attr.field_type == UIFieldType.TEXT)
        self.assertEqual(attr_match, True)

    def test_database_api(self):
        self.client.emit('load_data', {'load_types': ['pilot_data']})
        ld_pilots = self.get_response('pilot_data')['pilots']
        db_pilots = server.RHAPI.db.pilots
        num_pilots = len(server.RHAPI.db.pilots)
        self.assertGreater(num_pilots, 0)
        num_matched = 0
        for ld_pilot in ld_pilots:
            for db_pilot in db_pilots:
                if ld_pilot['pilot_id'] == db_pilot.id and ld_pilot['callsign'] == db_pilot.callsign and \
                            ld_pilot['phonetic'] == db_pilot.phonetic and ld_pilot['name'] == db_pilot.name and \
                            ld_pilot['team'] == db_pilot.team and ld_pilot['color'] == db_pilot.color and \
                            ld_pilot['active'] == db_pilot.active:
                    num_matched += 1
        self.assertGreater(num_matched, 0)
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
        self.assertGreater(num_matched, 0)
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

        self.client.emit('load_data', {'load_types': ['heat_data']})
        ld_heats = self.get_response('heat_data')['heats']
        db_heats = server.RHAPI.db.heats
        num_heats = len(server.RHAPI.db.heats)
        self.assertGreater(num_pilots, 0)
        num_matched = 0        
        for ld_heat in ld_heats:
            for db_heat in db_heats:
                if ld_heat['id'] == db_heat.id and \
                   ld_heat['name'] == db_heat.name and \
                   ld_heat['displayname'] == db_heat.display_name and \
                   ld_heat['class_id'] == db_heat.class_id and \
                   ld_heat['order'] == db_heat.order and \
                   ld_heat['status'] == db_heat.status and \
                   ld_heat['auto_frequency'] == db_heat.auto_frequency:
                    num_matched += 1
        self.assertGreater(num_matched, 0)
        self.assertEqual(len(ld_heats), len(db_heats))
        self.assertEqual(num_matched, len(db_heats))

        ld_heat['name'] = 'Test Name'
        ld_heat['class_id'] = 1
        ld_heat['auto_frequency'] = False 
        new_heat = server.RHAPI.db.heat_add(name=ld_heat['name'], raceclass=ld_heat['class_id'], auto_frequency=ld_heat['auto_frequency'])
        self.assertNotEqual(new_heat, None)
        self.assertEqual(len(server.RHAPI.db.heats), num_heats+1)
        db_heat = server.RHAPI.db.heat_by_id(new_heat.id)
        self.assertNotEqual(db_heat, None)
        db_heat_match = (ld_heat['name'] == db_heat.name and \
                   ld_heat['class_id'] == db_heat.class_id and \
                   ld_heat['auto_frequency'] == db_heat.auto_frequency)
        self.assertEqual(db_heat_match, True)
        ld_heat['name'] = 'Test Name 2'
        ld_heat['class_id'] = 2
        ld_heat['auto_frequency'] = True 
        new_heat2, race_list = server.RHAPI.db.heat_alter(new_heat.id, name=ld_heat['name'], raceclass=ld_heat['class_id'], auto_frequency=ld_heat['auto_frequency'])

        self.assertNotEqual(new_heat2, None)
        self.assertNotEqual(race_list, None)
        db_heat = server.RHAPI.db.heat_by_id(new_heat.id)
        self.assertNotEqual(db_heat, None)
        self.assertEqual(db_heat.id, new_heat2.id)
        db_heat_match = (ld_heat['name'] == db_heat.name and \
                           ld_heat['class_id'] == db_heat.class_id and \
                           ld_heat['auto_frequency'] == db_heat.auto_frequency)
        self.assertEqual(db_heat_match, True)
        result_flag = server.RHAPI.db.heat_delete(new_heat.id)
        self.assertEqual(result_flag, True)
        self.assertEqual(len(server.RHAPI.db.heats), num_heats)

    def test_race_api(self):
        server.RHAPI.db.heat_add()
        server.RHAPI.race.heat = 0
        self.assertEqual(server.RHAPI.race.heat, 0)
        server.RHAPI.race.heat = 1
        self.assertEqual(server.RHAPI.race.heat, 1)

    def test_attributes(self):
        # Ensure there is a stored pilot, heat, class, and race
        server.RHAPI.db.pilot_add()
        server.RHAPI.db.heat_add()
        server.RHAPI.db.raceclass_add()
        server.RHAPI.race.stage()
        server.RHAPI.race.stop()
        server.RHAPI.race.save()

        pilot = server.RHAPI.db.pilots[0]
        heat = server.RHAPI.db.heats[0]
        raceclass = server.RHAPI.db.raceclasses[0]
        race = server.RHAPI.db.races[0]
        format = server.RHAPI.db.raceformats[0]

        server.RHAPI.db.pilot_alter(pilot.id, attributes={'test_attribute': 'test-pilot-attr'})
        server.RHAPI.db.heat_alter(heat.id, attributes={'test_attribute': 'test-heat-attr'})
        server.RHAPI.db.raceclass_alter(raceclass.id, attributes={'test_attribute': 'test-raceclass-attr'})
        server.RHAPI.db.race_alter(race.id, attributes={'test_attribute': 'test-race-attr'})
        server.RHAPI.db.raceformat_alter(format.id, attributes={'test_attribute': 'test-format-attr'})

        attributes_by_obj = server.RHAPI.db.pilot_attributes(pilot)
        #attributes_by_id = server.RHAPI.db.pilot_attributes(pilot.id)
        #self.assertEqual(attributes_by_obj, attributes_by_id)
        attr_by_obj = server.RHAPI.db.pilot_attribute_value(pilot, 'test_attribute')
        self.assertEqual(attr_by_obj, 'test-pilot-attr')

        attributes_by_obj = server.RHAPI.db.heat_attributes(heat)
        #attributes_by_id = server.RHAPI.db.heat_attributes(heat.id)
        #self.assertEqual(attributes_by_obj, attributes_by_id)
        attr_by_obj = server.RHAPI.db.heat_attribute_value(heat, 'test_attribute')
        self.assertEqual(attr_by_obj, 'test-heat-attr')

        attributes_by_obj = server.RHAPI.db.raceclass_attributes(raceclass)
        #attributes_by_id = server.RHAPI.db.raceclass_attributes(raceclass.id)
        #self.assertEqual(attributes_by_obj, attributes_by_id)
        attr_by_obj = server.RHAPI.db.raceclass_attribute_value(raceclass, 'test_attribute')
        self.assertEqual(attr_by_obj, 'test-raceclass-attr')

        attributes_by_obj = server.RHAPI.db.race_attributes(race)
        #attributes_by_id = server.RHAPI.db.race_attributes(race.id)
        #self.assertEqual(attributes_by_obj, attributes_by_id)
        attr_by_obj = server.RHAPI.db.race_attribute_value(race, 'test_attribute')
        self.assertEqual(attr_by_obj, 'test-race-attr')

        attributes_by_obj = server.RHAPI.db.raceformat_attributes(format)
        #attributes_by_id = server.RHAPI.db.raceformat_attributes(format.id)
        #self.assertEqual(attributes_by_obj, attributes_by_id)
        attr_by_obj = server.RHAPI.db.raceformat_attribute_value(format, 'test_attribute')
        self.assertEqual(attr_by_obj, 'test-format-attr')

    def test_rhapi_frequencyset(self):
        original_set = server.RHAPI.race.frequencyset
        num_sets = len(server.RHAPI.db.frequencysets)
        frequencyset_1 = server.RHAPI.db.frequencyset_add()
        frequencyset_2 = server.RHAPI.db.frequencyset_add()
        self.assertEqual(num_sets + 2, len(server.RHAPI.db.frequencysets))
        self.assertNotEqual(frequencyset_1.id, frequencyset_2.id)
        server.RHAPI.race.frequencyset = frequencyset_1.id
        self.assertEqual(server.RHAPI.race.frequencyset.id, frequencyset_1.id)
        server.RHAPI.race.frequencyset = frequencyset_2.id
        self.assertEqual(server.RHAPI.race.frequencyset.id, frequencyset_2.id)
        server.RHAPI.race.frequencyset = original_set.id
        result = server.RHAPI.db.frequencyset_delete(frequencyset_1)
        self.assertEqual(result, True)
        result = server.RHAPI.db.frequencyset_delete(frequencyset_2.id)
        self.assertEqual(result, True)
        self.assertEqual(num_sets, len(server.RHAPI.db.frequencysets))

    def test_rhapi_format(self):
        server.RHAPI.race.stop()
        server.RHAPI.race.clear()
        num_formats = len(server.RHAPI.db.raceformats)
        format_1 = server.RHAPI.db.raceformat_add(name="RaceFormat Test {}".format(num_formats + 1))
        format_2 = server.RHAPI.db.raceformat_add(name="RaceFormat Test {}".format(num_formats + 2))
        self.assertEqual(num_formats + 2, len(server.RHAPI.db.raceformats))
        self.assertNotEqual(format_1.id, format_2.id)
        server.RHAPI.race.raceformat = format_1.id
        self.assertEqual(server.RHAPI.db.raceformat_by_id(format_1.id).name, server.RHAPI.race.raceformat.name)
        server.RHAPI.race.raceformat = format_2.id
        self.assertEqual(server.RHAPI.db.raceformat_by_id(format_2.id).name, server.RHAPI.race.raceformat.name)
        server.RHAPI.race.raceformat = 1
        result = server.RHAPI.db.raceformat_delete(format_1.id)
        self.assertEqual(result, True)
        result = server.RHAPI.db.raceformat_delete(format_2.id)
        self.assertEqual(result, True)
        self.assertEqual(num_formats, len(server.RHAPI.db.raceformats))

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
