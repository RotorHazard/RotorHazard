'''Sensor class for the hardware interface.'''
from interface.Plugins import Plugins

def Reading(units):
    def decorator(func):
        func.units = units
        return func
    return decorator

class Sensor:
    def __init__(self, name):
        self.name = name

    def getReadings(self):
        readings = {}
        for fname in dir(self):
            f = getattr(self, fname)
            if hasattr(f, 'units'):
                readings[f.__name__] = {'value': f(), 'units': f.units}
        return readings

    def update(self):
        pass

class I2CSensor(Sensor):
    @staticmethod
    def url(addr):
        return 'i2c:' + hex(addr)

    def __init__(self, name, i2c_bus):
        super().__init__(name=name)
        self.i2c_bus = i2c_bus

    def update(self):
        self.i2c_bus.with_i2c_quietly(self._readData)

class Sensors(Plugins):
    def __init__(self):
        super().__init__(suffix='sensor')
        self.environmental_data_update_tracker = 0

    def update_environmental_data(self):
        '''Updates environmental data.'''
        self.environmental_data_update_tracker += 1

        partition = (self.environmental_data_update_tracker % 2)
        for index, sensor in enumerate(self.data):
            if (index % 2) == partition:
                sensor.update()
