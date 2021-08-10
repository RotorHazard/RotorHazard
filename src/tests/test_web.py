import unittest
from server import web

class WebTest(unittest.TestCase):
    def test_ifpv(self):
        data = web.get_pilot_data('https://league.ifpv.co.uk/pilots/220')
        self.assertEqual(data['name'], 'Jon Totham')
        self.assertEqual(data['callsign'], 'Vaxel')
        self.assertEqual(data['logo'], 'https://league.ifpv.co.uk/storage/images/pilots/1515246538.gif')

    def test_multigp(self):
        data = web.get_pilot_data('https://www.multigp.com/pilots/view/?pilot=SeekND')
        self.assertEqual(data['logo'], 'https://multigp-storage-new.s3.us-east-2.amazonaws.com/user/1135/profileImage-20.png')

if __name__ == '__main__':
    unittest.main()
