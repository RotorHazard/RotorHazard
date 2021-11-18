import unittest
from server import web

class WebTest(unittest.TestCase):
    def test_ifpv(self):
        url = 'https://league.ifpv.co.uk/pilots/220'
        data = web.get_pilot_data(url)
        if not data:
            print("Skipping test - could not connect to {}".format(url))
            return

        self.assertEqual(data['name'], 'Jon Totham')
        self.assertEqual(data['callsign'], 'Vaxel')
        self.assertEqual(data['logo'], 'https://league.ifpv.co.uk/storage/images/pilots/1515246538.gif')

    def test_multigp(self):
        url  = 'https://www.multigp.com/pilots/view/?pilot=SeekND'
        data = web.get_pilot_data(url)
        if not data:
            print("Skipping test - could not connect to {}".format(url))
            return

        self.assertEqual(data['logo'], 'https://multigp-storage-new.s3.us-east-2.amazonaws.com/user/1135/profileImage-20.png')

if __name__ == '__main__':
    unittest.main()
