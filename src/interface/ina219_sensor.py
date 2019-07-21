from sensor import I2CSensor, Reading
import ina219

class INA219Sensor(I2CSensor):
    def __init__(self, name, addr, i2c_helper):
        I2CSensor.__init__(self, name, i2c_helper)
        self.device = ina219.INA219(0.1, address=addr)
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
