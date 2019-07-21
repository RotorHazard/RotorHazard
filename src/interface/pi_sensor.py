# coding=UTF-8

from sensor import Sensor, Reading

class PiSensor(Sensor):
    def __init__(self, name):
        Sensor.__init__(self, name)
        self.update()

    def update(self):
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            self.core_temperature = float(f.read())/1000

    @Reading(units='°C')
    def temperature(self):
        return self.core_temperature
