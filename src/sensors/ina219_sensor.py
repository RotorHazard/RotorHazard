import logging
from . import I2CSensor, Reading
import ina219

logger = logging.getLogger(__name__)


class INA219Sensor(I2CSensor):
    def __init__(self, name, addr, i2c_bus, config={}):
        super().__init__(name=name, i2c_addr=addr, i2c_bus=i2c_bus)
        self.description = 'INA219'
        max_current = float(config['max_current']) if 'max_current' in config else None
        self.device = ina219.INA219(0.1, address=addr, max_expected_amps=max_current)
        self.device.configure()
        self.device.sleep()
        self._readData()

    def _readData(self):
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


def discover(config, i2c_helper, *args, **kwargs):
    sensors = []
    supported_ina219_addrs = [0x40, 0x41, 0x44, 0x45]
    for i2c_bus in i2c_helper:
        for addr in supported_ina219_addrs:
            url = i2c_bus.url_of(addr)
            sensor_config = config.get(url, {})
            if sensor_config.get('enabled', True):
                name = sensor_config.get('name', url)
                try:
                    sensors.append(INA219Sensor(name, addr, i2c_bus, sensor_config))
                except IOError:
                    lvl = logging.INFO if sensor_config else logging.DEBUG
                    logger.log(lvl, "No INA219 found on bus {} at address 0x{:#02x}".format(i2c_bus.id, addr))
    return sensors
