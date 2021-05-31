import unittest

from sensors import Sensors, I2CSensor
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

    def test_i2c_sensor(self):
        class MockI2CBus:
            pass

        i2c_bus = MockI2CBus()
        i2c_bus.id = 1
        sensor = I2CSensor('i2c test', 8, i2c_bus)
        self.assertEqual(sensor.url, 'i2c:1/0x08')
        self.assertEqual(sensor.name, 'i2c test')
        self.assertEqual(sensor.i2c_address, 8)
        self.assertEqual(sensor.i2c_bus.id, 1)

if __name__ == '__main__':
    unittest.main()
