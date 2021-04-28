import unittest

from sensors import Sensors
import tests as tests_pkg

class SensorsTest(unittest.TestCase):
    def setUp(self):
        self.sensors = Sensors()

    def tearDown(self):
        pass

    def test_update(self):
        self.sensors.discover(tests_pkg)
        self.assertEqual(len(self.sensors), 1)
        before = self.sensors[0].getReadings()
        self.sensors.update_environmental_data()
        self.sensors.update_environmental_data()
        after = self.sensors[0].getReadings()
        self.assertEqual(after['counter']['value'], before['counter']['value']+1)

if __name__ == '__main__':
    unittest.main()
