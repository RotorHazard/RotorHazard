# coding=UTF-8
import logging

from . import I2CSensor, Reading
import bme280

logger = logging.getLogger(__name__)


class BME280Sensor(I2CSensor):
    def __init__(self, name, addr, i2c_bus):
        super().__init__(name=name, i2c_bus=i2c_bus)
        self.address = addr
        self._readData()

    def _readData(self):
        self.data = bme280.sample(self.i2c_bus.i2c, self.address)

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
    for i2c_bus in i2c_helper:
        for addr in supported_bme280_addrs:
            url = I2CSensor.url(addr)
            sensor_config = config.get(url, {})
            name = sensor_config.get('name', url)
            try:
                sensors.append(BME280Sensor(name, addr, i2c_bus))
                logger.info("BME280 found on bus {} at address 0x{:02x} ('{}')".format(i2c_bus.id, addr, name))
            except IOError:
                lvl = logging.INFO if sensor_config else logging.DEBUG
                logger.log(lvl, "No BME280 found on bus {} at address 0x{:02x}".format(i2c_bus.id, addr))
    return sensors
