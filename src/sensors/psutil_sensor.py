# coding=UTF-8

import psutil
from . import Sensor, Reading


class TemperatureSensor(Sensor):
    def __init__(self, name, subname):
        fullname = "{} ({})".format(name, subname) if subname else name
        Sensor.__init__(self, fullname)
        self.subname = subname
        self.update()

    def update(self):
        temps = psutil.sensors_temperatures()
        self._temp = next(filter(lambda s: s.label==self.subname, temps[self.name]), None).current

    @Reading(units='°C')
    def temperature(self):
        return self._temp

class FanSensor(Sensor):
    def __init__(self, name, subname):
        fullname = "{} ({})".format(name, subname) if subname else name
        Sensor.__init__(self, fullname)
        self.subname = subname
        self.update()

    def update(self):
        fans = psutil.sensors_fans()
        self._rpm = next(filter(lambda s: s.label==self.subname, fans[self.name]), None).current

    @Reading(units='rpm')
    def speed(self):
        return self._rpm

class BatterySensor(Sensor):
    def __init__(self, name):
        Sensor.__init__(self, name)
        self.update()

    def update(self):
        batt = psutil.sensors_battery()
        self._capacity = batt.percent

    @Reading(units='%')
    def capacity(self):
        return self._capacity


def discover(*args, **kwargs):
    sensors = []

    if hasattr(psutil, 'sensors_battery'):
        sensors.append(BatterySensor('Battery'))

    if hasattr(psutil, 'sensors_temperatures'):
        temps = psutil.sensors_temperatures()
        for name, slist in temps.items():
            for s in slist:
                sensors.append(TemperatureSensor(name, s.label))

    if hasattr(psutil, 'sensors_fans'):
        fans = psutil.sensors_fans()
        for name, slist in fans.items():
            for s in slist:
                sensors.append(FanSensor(name, s.label))

    return sensors
