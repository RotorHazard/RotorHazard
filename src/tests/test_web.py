import unittest
import json
from server import web
from rh.orgs import ifpv_org

web.init(None)

class WebTest(unittest.TestCase):
    def test_ifpv_pilot(self):
        url = 'https://league.ifpv.co.uk/pilots/220'
        data = web.get_pilot_data(url)
        if not data:
            print("Skipping test - could not connect to {}".format(url))
            return

        self.assertEqual(data['name'], 'Jon Totham')
        self.assertEqual(data['callsign'], 'Vaxel')
        self.assertEqual(data['logo'], 'https://league.ifpv.co.uk/storage/images/pilots/1515246538.gif')

    def test_ifpv_event(self):
        with open('tests/test_ifpv_event.json') as f:
            ifpv_json = json.loads(f.read())
        ifpv = ifpv_org.Ifpv()
        actual_json = ifpv.convert_ifpv_json(ifpv_json)
        with open('tests/test_converted_ifpv_event.json') as f:
            expected_json = json.loads(f.read())
        self.assertDictEqual(actual_json, expected_json)

    def test_multigp(self):
        url  = 'https://www.multigp.com/pilots/view/?pilot=SeekND'
        data = web.get_pilot_data(url)
        if not data:
            print("Skipping test - could not connect to {}".format(url))
            return

        self.assertEqual(data['logo'], 'https://multigp-storage-new.s3.us-east-2.amazonaws.com/user/1135/profileImage-20.png')


if __name__ == '__main__':
    unittest.main()
