"""Receiver tuning contracts, lifecycle, and authenticated HTTP operations."""
import base64
import unittest
from unittest.mock import Mock

import test_server  # uses mock timing hardware and a fresh temporary data directory
import server


class SensorTuningTest(unittest.TestCase):
    def setUp(self):
        server.rh_program_initialize(reg_endpoints_flag=False)
        self.client = server.APP.test_client()
        self.snapshot = {'connected': True, 'nodes': [{
            'index': 0, 'frequency': 5658, 'enter': 72, 'exit': 68,
            'rssi': 30, 'peak': 40, 'nadir': 20, 'inside': False,
        }]}
        self.write = Mock(return_value={'ok': True, 'enter': 72, 'exit': 68})
        self.capture = Mock(return_value={'ok': True, 'enter': 75, 'exit': 68})
        server.RHAPI.ui.register_sensor_tuning('split-test', 'Split test', lambda: self.snapshot,
                                              self.write, self.capture)

    def test_snapshot_does_not_add_seats(self):
        before = server.RaceContext.race.num_nodes
        response = self.client.get('/sensor-tuning/data')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        provider = response.json['providers'][0]
        self.assertEqual(provider['label'], 'Split test')
        self.assertTrue(provider['can_capture'])
        self.assertEqual(server.RaceContext.race.num_nodes, before)

    def test_registration_replacement_and_removal(self):
        server.RHAPI.ui.register_sensor_tuning('split-test', 'Replacement', lambda: self.snapshot, self.write)
        providers = self.client.get('/sensor-tuning/data').json['providers']
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]['label'], 'Replacement')
        self.assertFalse(providers[0]['can_capture'])
        self.assertTrue(server.RHAPI.ui.unregister_sensor_tuning('split-test'))
        self.assertFalse(server.RHAPI.ui.unregister_sensor_tuning('split-test'))
        self.assertEqual(self.client.get('/sensor-tuning/data').json['providers'], [])

    def test_registration_cleared_before_initialize(self):
        server.rh_program_initialize(reg_endpoints_flag=False)
        self.assertEqual(self.client.get('/sensor-tuning/data').json['providers'], [])

    def test_invalid_registration(self):
        for name in ('', 'a/b', '<receiver>', 'contains space', None):
            with self.assertRaises(ValueError):
                server.RHAPI.ui.register_sensor_tuning(name, 'Test', lambda: self.snapshot, self.write)

    def test_bad_provider_does_not_break_other_receivers(self):
        server.RHAPI.ui.register_sensor_tuning('bad', 'Bad receiver', lambda: {'connected': True, 'nodes': None}, self.write)
        providers = self.client.get('/sensor-tuning/data').json['providers']
        self.assertTrue(providers[0]['connected'])
        self.assertFalse(providers[1]['connected'])
        self.assertEqual(providers[1]['nodes'], [])
        self.snapshot['nodes'][0]['rssi'] = float('nan')
        self.assertFalse(self.client.get('/sensor-tuning/data').json['providers'][0]['connected'])

    def test_callback_can_unregister_without_breaking_snapshot_iteration(self):
        def remove_self():
            server.RHAPI.ui.unregister_sensor_tuning('self-removing')
            return self.snapshot
        server.RHAPI.ui.register_sensor_tuning('self-removing', 'Self removing', remove_self, self.write)
        self.assertEqual(self.client.get('/sensor-tuning/data').status_code, 200)
        self.assertEqual(len(self.client.get('/sensor-tuning/data').json['providers']), 1)

    def test_unknown_callback_fields_do_not_leak_into_json(self):
        self.snapshot['private-object'] = object()
        self.snapshot['nodes'][0]['private-object'] = object()
        provider = self.client.get('/sensor-tuning/data').json['providers'][0]
        self.assertNotIn('private-object', provider)
        self.assertNotIn('private-object', provider['nodes'][0])

    def test_write_requires_strict_valid_thresholds(self):
        for data in ({'enter': 72.9, 'exit': 68}, {'enter': True, 'exit': 0},
                     {'enter': 68, 'exit': 68}, {'enter': 72, 'exit': -1}, {}, []):
            self.assertEqual(self.client.post('/sensor-tuning/split-test/0', json=data).status_code, 400)
        self.write.assert_not_called()
        response = self.client.post('/sensor-tuning/split-test/0', json={'enter': 72, 'exit': 68})
        self.assertEqual(response.status_code, 200)
        self.write.assert_called_once_with(0, 72, 68)
        self.assertEqual(response.json, {'ok': True, 'enter': 72, 'exit': 68})

    def test_write_failure_is_not_reported_as_saved(self):
        self.write.side_effect = RuntimeError('hardware unavailable')
        response = self.client.post('/sensor-tuning/split-test/0', json={'enter': 72, 'exit': 68})
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.json['ok'])
        self.write.side_effect = None
        self.write.return_value = {'ok': True}
        self.assertEqual(self.client.post('/sensor-tuning/split-test/0', json={'enter': 72, 'exit': 68}).status_code, 502)

    def test_capture_dispatch_and_validation(self):
        response = self.client.post('/sensor-tuning/split-test/0/capture', json={'level': 'enter'})
        self.assertEqual(response.status_code, 200)
        self.capture.assert_called_once_with(0, 'enter')
        self.assertEqual(response.json['enter'], 75)
        self.assertEqual(self.client.post('/sensor-tuning/split-test/0/capture', json={'level': 'other'}).status_code, 400)
        server.RHAPI.ui.register_sensor_tuning('no-capture', 'No capture', lambda: self.snapshot, self.write)
        self.assertEqual(self.client.post('/sensor-tuning/no-capture/0/capture', json={'level': 'enter'}).status_code, 400)

    def test_all_receiver_routes_require_authentication(self):
        config = server.RaceContext.serverconfig
        previous_secrets = config.config['SECRETS'].copy()
        previous_status = config.config_file_status
        config.config['SECRETS'].update(ADMIN_USERNAME='test-admin', ADMIN_PASSWORD='test-password')
        config.config_file_status = 1
        try:
            self.assertEqual(self.client.get('/sensor-tuning/data').status_code, 401)
            self.assertEqual(self.client.post('/sensor-tuning/split-test/0', json={'enter': 72, 'exit': 68}).status_code, 401)
            self.assertEqual(self.client.post('/sensor-tuning/split-test/0/capture', json={'level': 'enter'}).status_code, 401)
            header = {'Authorization': 'Basic ' + base64.b64encode(b'test-admin:test-password').decode()}
            self.assertEqual(self.client.get('/sensor-tuning/data', headers=header).status_code, 200)
            self.write.assert_not_called()
            self.capture.assert_not_called()
        finally:
            config.config['SECRETS'] = previous_secrets
            config.config_file_status = previous_status


if __name__ == '__main__':
    unittest.main()
