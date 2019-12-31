from sensor import I2CSensor, Reading
import ina219

class INA219Sensor(I2CSensor):
    def __init__(self, name, addr, i2c_helper, config={}):
        I2CSensor.__init__(self, name, i2c_helper)
        max_current = float(config['max_current']) if 'max_current' in config else None
        self.device = ina219.INA219(0.1, address=addr, max_expected_amps=max_current)
        self.device.configure()
        self.device.sleep()
        self.readData()

    def readData(self):
        self.device.wake()
        self._voltage = self.device.voltage()
        self._current = self.device.current()
        self._power = self.device.power()
        self.device.sleep()

    @Reading(units='V')
    def voltage(self):
        return self._voltage

    @Reading(units='mA')
    def current(self):
        return self._current

    @Reading(units='mW')
    def power(self):
        return self._power


def discover(config, *args, **kwargs):
    if 'i2c_helper' not in kwargs:
        return []

    sensors = []
    i2c_helper = kwargs['i2c_helper']
    supported_ina219_addrs = [0x40, 0x41, 0x44, 0x45]
    for addr in supported_ina219_addrs:
        url = I2CSensor.url(addr)
        sensor_config = config.get(url, {})
        name = sensor_config.get('name', url)
        try:
            sensors.append(INA219Sensor(name, addr, i2c_helper, sensor_config))
            print "INA219 found at address {0}".format(addr)
        except IOError:
            print "No INA219 at address {0}".format(addr)
    return sensors
