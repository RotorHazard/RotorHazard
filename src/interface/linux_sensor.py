# coding=UTF-8

import logging
from sensor import Sensor, Reading

logger = logging.getLogger(__name__)


class TemperatureSensor(Sensor):
    def __init__(self, name):
        Sensor.__init__(self, name)
        self.update()

    def update(self):
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            self._temp = float(f.read())/1000.0

    @Reading(units='°C')
    def temperature(self):
        return self._temp

class BatterySensor(Sensor):
    def __init__(self, name):
        Sensor.__init__(self, name)
        self.update()

    def update(self):
        with open('/sys/class/power_supply/battery/temp', 'r') as f:
            self._temp = float(f.read())/10.0
        with open('/sys/class/power_supply/battery/current_now', 'r') as f:
            self._current = float(f.read())/1000.0
        with open('/sys/class/power_supply/battery/voltage_now', 'r') as f:
            self._voltage = float(f.read())/1000000.0
        with open('/sys/class/power_supply/battery/capacity', 'r') as f:
            self._capacity = float(f.read())

    @Reading(units='°C')
    def temperature(self):
        return self._temp

    @Reading(units='A')
    def current(self):
        return self._current

    @Reading(units='V')
    def voltage(self):
        return self._voltage

    @Reading(units='Ah')
    def capacity(self):
        return self._capacity


def discover(*args, **kwargs):
    sensors = []

    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            sensors.append(TemperatureSensor('Core'))
        logger.info('Core temperature available')
    except Exception as err:
        logger.debug('Core temperature not available ({0})'.format(err))

    try:
        with open('/sys/class/power_supply/battery/present', 'r') as f:
            if int(f.read()) == 1:
                sensors.append(BatterySensor('Battery'))
                logger.info('Battery status available')
    except Exception as err:
        logger.debug('Battery status not available ({0})'.format(err))

    return sensors
