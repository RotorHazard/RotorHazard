# coding=UTF-8

import logging
from . import Sensor, Reading

logger = logging.getLogger(__name__)

def file_url(file):
    return 'file://' + file

class TemperatureSensor(Sensor):
    def __init__(self, file, name):
        super().__init__(self, url=file_url(file), name=name)
        self.file = file
        self.description = 'Core temperature'
        self.update()

    def update(self):
        with open(self.file, 'r') as f:
            self._temp = float(f.read())/1000.0

    @Reading(units='°C')
    def temperature(self):
        return self._temp

class BatterySensor(Sensor):
    def __init__(self, file, name):
        super().__init__(self, url=file_url(file), name=name)
        self.file = file
        self.description = 'Battery'
        self.update()

    def update(self):
        with open(self.file+'/temp', 'r') as f:
            self._temp = float(f.read())/10.0
        with open(self.file+'/current_now', 'r') as f:
            self._current = float(f.read())/1000.0
        with open(self.file+'/voltage_now', 'r') as f:
            self._voltage = float(f.read())/1000000.0
        with open(self.file+'/capacity', 'r') as f:
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


def discover(config, *args, **kwargs):
    sensors = []

    file = '/sys/class/thermal/thermal_zone0/temp'
    url = file_url(file)
    sensor_config = config.get(url, {})
    if sensor_config.get('enabled', True):
        try:
            with open(file, 'r') as f:
                name = sensor_config.get('name', 'Core')
                sensors.append(TemperatureSensor(file, name))
        except IOError as err:
            lvl = logging.INFO if sensor_config else logging.DEBUG
            logger.log(lvl, 'Core temperature not available ({0})'.format(err))

    file = '/sys/class/power_supply/battery'
    url = file_url(file)
    sensor_config = config.get(url, {})
    if sensor_config.get('enabled', True):
        try:
            with open(file+'/present', 'r') as f:
                if int(f.read()) == 1:
                    name = sensor_config.get('name', 'Battery')
                    sensors.append(BatterySensor(file, name))
        except IOError as err:
            lvl = logging.INFO if sensor_config else logging.DEBUG
            logger.log(lvl, 'Battery status not available ({0})'.format(err))

    return sensors
