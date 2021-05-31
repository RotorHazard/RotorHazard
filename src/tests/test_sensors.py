import unittest

from sensors import Sensors, I2CSensor
import sys
import fake_rpi
sys.modules['smbus'] = fake_rpi.smbus

from helpers.i2c_helper import I2CBus
import tests as tests_pkg

class SensorsTest(unittest.TestCase):
    def setUp(self):
        self.i2c_bus = I2CBus(1)
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
        sensor = I2CSensor('i2c test', 8, self.i2c_bus)
        self.assertEqual(sensor.url, 'i2c:1/0x08')
        self.assertEqual(sensor.name, 'i2c test')
        self.assertEqual(sensor.i2c_address, 8)
        self.assertEqual(sensor.i2c_bus.id, 1)


if __name__ == '__main__':
    unittest.main()
