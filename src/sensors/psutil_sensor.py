# coding=UTF-8

import psutil
from . import Sensor, Reading

def psutil_sensor_url(unit_name, sub_label):
    return "psutil:{}/{}".format(unit_name, sub_label)

def psutil_sensor_name(unit_name, sub_label):
    return "{} ({})".format(unit_name, sub_label)

class PsUtilSensor(Sensor):
    def __init__(self, name, unit_name, sub_label):
        super().__init__(url=psutil_sensor_url(unit_name, sub_label), name=name)
        self.unit_name = unit_name
        self.sub_label = sub_label
        self.update()

class TemperatureSensor(PsUtilSensor):
    def __init__(self, name, unit_name, sub_label):
        super().__init__(name=name, unit_name=unit_name, sub_label=sub_label)
        self.description = 'Temperature'

    def update(self):
        temps = psutil.sensors_temperatures()
        self._temp = next(filter(lambda s: s.label==self.sub_label, temps[self.unit_name]), None).current

    @Reading(units='°C')
    def temperature(self):
        return self._temp

class FanSensor(PsUtilSensor):
    def __init__(self, name, unit_name, sub_label):
        super().__init__(name=name, unit_name=unit_name, sub_label=sub_label)
        self.description = 'Fan'

    def update(self):
        fans = psutil.sensors_fans()
        self._rpm = next(filter(lambda s: s.label==self.sub_label, fans[self.unit_name]), None).current

    @Reading(units='rpm')
    def speed(self):
        return self._rpm

class BatterySensor(PsUtilSensor):
    def __init__(self, name, unit_name, sub_label):
        super().__init__(name=name, unit_name=unit_name, sub_label=sub_label)
        self.description = 'Battery'

    def update(self):
        batt = psutil.sensors_battery()
        self._capacity = batt.percent

    @Reading(units='%')
    def capacity(self):
        return self._capacity


def discover(config, *args, **kwargs):
    sensors = []

    if hasattr(psutil, 'sensors_battery'):
        unit_name = 'battery'
        sub_label = ''
        url = psutil_sensor_url(unit_name, sub_label)
        sensor_config = config.get(url, {})
        if sensor_config.get('enabled', True) and psutil.sensors_battery():
            name = sensor_config.get('name', 'Battery')
            sensors.append(BatterySensor(name, unit_name, sub_label))

    if hasattr(psutil, 'sensors_temperatures'):
        temps = psutil.sensors_temperatures()
        for unit_name, sub_sensors in temps.items():
            for sub_sensor in sub_sensors:
                sub_label = sub_sensor.label
                url = psutil_sensor_url(unit_name, sub_label)
                sensor_config = config.get(url, {})
                if sensor_config.get('enabled', True):
                    name = sensor_config.get('name', psutil_sensor_name(unit_name, sub_label))
                    sensors.append(TemperatureSensor(name, unit_name, sub_label))

    if hasattr(psutil, 'sensors_fans'):
        fans = psutil.sensors_fans()
        for unit_name, sub_sensors in fans.items():
            for sub_sensor in sub_sensors:
                sub_label = sub_sensor.label
                url = psutil_sensor_url(unit_name, sub_label)
                sensor_config = config.get(url, {})
                if sensor_config.get('enabled', True):
                    name = sensor_config.get('name', psutil_sensor_name(unit_name, sub_label))
                    sensors.append(FanSensor(name, unit_name, sub_label))

    return sensors
