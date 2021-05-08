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
        self.assertEqual(data['logo'], 'https://s3.amazonaws.com/multigp-storage/user/1135/profile-picture.jpg')

if __name__ == '__main__':
    unittest.main()
