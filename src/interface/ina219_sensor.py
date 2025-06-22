import logging
from sensor import I2CSensor, Reading
import ina219  # @UnresolvedImport pylint: disable=import-error

logger = logging.getLogger(__name__)


class INA219Sensor(I2CSensor):
    def __init__(self, name, addr, i2c_helper, config={}):  #pylint: disable=dangerous-default-value
        I2CSensor.__init__(self, name, i2c_helper)
        self.address = addr
        max_current = float(config['max_current']) if 'max_current' in config else None
        self.device = ina219.INA219(0.1, address=addr, max_expected_amps=max_current,
                                    busnum=i2c_helper.get_i2c_busnum())
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


def discover(config, i2c_helper, *args, **kwargs):
    sensors = []
    supported_ina219_addrs = [0x40, 0x41, 0x44, 0x45]
    for addr in supported_ina219_addrs:
        url = I2CSensor.url(addr)
        sensor_config = config.get(url, {})
        name = sensor_config.get('name', "Battery")
        try:
            sensors.append(INA219Sensor(name, addr, i2c_helper, sensor_config))
            logger.info("INA219 found at address 0x{:02x} ('{}')".format(addr, name))
        except IOError:
            if sensor_config:
                logger.info("No INA219 found at address 0x{:02x}".format(addr))
    return sensors
