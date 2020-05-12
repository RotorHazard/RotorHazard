# coding=UTF-8
import logging

from sensor import I2CSensor, Reading

logger = logging.getLogger(__name__)


class BME280Sensor(I2CSensor):
    def __init__(self, name, addr, bme280, i2c_helper):
        I2CSensor.__init__(self, name, i2c_helper)
        self.address = addr
        self.bme280 = bme280
        self.readData()

    def readData(self):
        self.data = self.bme280.sample(self.i2c_helper.i2c, self.address)

    @Reading(units='°C')
    def temperature(self):
        return self.data.temperature

    @Reading(units='hPa')
    def pressure(self):
        return self.data.pressure

    @Reading(units='%rH')
    def humidity(self):
        return self.data.humidity


def discover(config, *args, **kwargs):
    if 'i2c_helper' not in kwargs:
        logger.debug("I2C bus not present")
        return []

    import bme280
    sensors = []
    i2c_helper = kwargs['i2c_helper']
    supported_bme280_addrs = [0x76, 0x77]
    for addr in supported_bme280_addrs:
        url = I2CSensor.url(addr)
        sensor_config = config.get(url, {})
        name = sensor_config.get('name', url)
        try:
            sensors.append(BME280Sensor(name, addr, bme280, i2c_helper))
            logger.info("BME280 found at address {0}".format(addr))
        except IOError:
            logger.info("No BME280 at address {0}".format(addr))
    return sensors
