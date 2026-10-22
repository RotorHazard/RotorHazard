'''Request-local HTTP authorization shared by native pages and plugin routes.'''
import base64
import os
import sys
import unittest
from types import SimpleNamespace
from flask import Flask

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))
import AdminAuth


class HttpAuthTest(unittest.TestCase):
    def setUp(self):
        self.credentials = {'ADMIN_USERNAME': 'organizer', 'ADMIN_PASSWORD': 'secret'}
        self.config = SimpleNamespace(config_file_status=1,
                                      get_item=lambda section, name: self.credentials.get(name))
        self.app = Flask(__name__)
        guard = AdminAuth.make_http_auth_guard(SimpleNamespace(serverconfig=self.config))

        @self.app.route('/manage')
        @guard
        def manage():
            return 'Organizer only'

        self.client = self.app.test_client()

    def authorized(self):
        token = base64.b64encode(b'organizer:secret').decode()
        return self.client.get('/manage', headers={'Authorization': 'Basic ' + token})

    def test_rejects_missing_and_wrong_credentials(self):
        response = self.client.get('/manage')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers['WWW-Authenticate'], 'Basic realm="Login Required"')
        token = base64.b64encode(b'organizer:wrong').decode()
        self.assertEqual(self.client.get('/manage', headers={
            'Authorization': 'Basic ' + token}).status_code, 401)

    def test_success_does_not_authorize_another_request(self):
        self.assertEqual(self.authorized().status_code, 200)
        self.assertEqual(self.client.get('/manage').status_code, 401)
        self.credentials['ADMIN_PASSWORD'] = 'changed'
        self.assertEqual(self.authorized().status_code, 401)

    def test_preserves_open_admin_and_first_run_policy(self):
        self.credentials.update(ADMIN_USERNAME='', ADMIN_PASSWORD='')
        self.assertEqual(self.client.get('/manage').status_code, 200)
        self.credentials.update(ADMIN_USERNAME='organizer', ADMIN_PASSWORD='secret')
        self.config.config_file_status = 0
        self.assertEqual(self.client.get('/manage').status_code, 200)
