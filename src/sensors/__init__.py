'''Sensor class for the hardware interface.'''
from interface.Plugins import Plugins
import logging

logger = logging.getLogger(__name__)

def Reading(units):
    def decorator(func):
        func.units = units
        return func
    return decorator

class Sensor:
    def __init__(self, url, name):
        self.url = url
        self.name = name
        self.description = ''

    def getMeasures(self):
        measures = []
        for fname in dir(self):
            f = getattr(self, fname)
            if hasattr(f, 'units'):
                measures.append(f.__name__)
        return measures

    def getReadings(self):
        readings = {}
        for fname in dir(self):
            f = getattr(self, fname)
            if hasattr(f, 'units'):
                value = f()
                if value is not None:
                    readings[f.__name__] = {'value': value, 'units': f.units}
        return readings

    def update(self):
        pass


class I2CSensor(Sensor):
    def __init__(self, name, i2c_addr, i2c_bus):
        super().__init__(url=i2c_bus.url_of(i2c_addr), name=name)
        self.i2c_address = i2c_addr
        self.i2c_bus = i2c_bus

    def update(self):
        self.i2c_bus.with_i2c_quietly(self._readData)


class Sensors(Plugins):
    def __init__(self):
        super().__init__(suffix='sensor')
        self.environmental_data_update_tracker = 0

    def _post_discover(self):
        for sensor in self:
            logger.info("{} ({}): {} ({})".format(sensor.name, sensor.url, sensor.description, ', '.join(sensor.getMeasures())))

    def update_environmental_data(self):
        '''Updates environmental data.'''
        self.environmental_data_update_tracker += 1

        partition = (self.environmental_data_update_tracker % 2)
        for index, sensor in enumerate(self.data):
            if (index % 2) == partition:
                sensor.update()
