# coding=UTF-8

from sensor import I2CSensor, Reading
import bme280

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


def discover(*args, **kwargs):
    sensors = []
    supported_bme280_addrs = [0x76, 0x77]
    for addr in supported_bme280_addrs:
        try:
            sensors.append(BME280Sensor(hex(addr), addr, kwargs['i2c_helper']))
            print "BME280 found at address {0}".format(addr)
        except IOError:
            print "No BME280 at address {0}".format(addr)
    return sensors
