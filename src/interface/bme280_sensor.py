# coding=UTF-8
import logging

from sensor import I2CSensor, Reading
import bme280  # @UnresolvedImport pylint: disable=import-error

logger = logging.getLogger(__name__)


class BME280Sensor(I2CSensor):
    def __init__(self, name, addr, i2c_helper):
        I2CSensor.__init__(self, name, i2c_helper)
        self.address = addr
        self.readData()

    def readData(self):
        self.data = bme280.sample(self.i2c_helper.i2c, self.address)

    @Reading(units='°C')
    def temperature(self):
        return self.data.temperature

    @Reading(units='hPa')
    def pressure(self):
        return self.data.pressure

    @Reading(units='%rH')
    def humidity(self):
        return self.data.humidity


def discover(config, i2c_helper, *args, **kwargs):
    sensors = []
    supported_bme280_addrs = [0x76, 0x77]
    for addr in supported_bme280_addrs:
        url = I2CSensor.url(addr)
        sensor_config = config.get(url, {})
        name = sensor_config.get('name', "Climate")
        try:
            sensors.append(BME280Sensor(name, addr, i2c_helper))
            logger.info("BME280 found at address 0x{:02x} ('{}')".format(addr, name))
        except IOError:
            if sensor_config:
                logger.info("No BME280 found at address 0x{:02x}".format(addr))
    return sensors
