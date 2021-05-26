'''Sensor class for the hardware interface.'''
from interface.Plugins import Plugins

def Reading(units):
    def decorator(func):
        func.units = units
        return func
    return decorator

class Sensor:
    def __init__(self, url, name):
        self.url = url
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

def i2c_url(bus_id, addr):
    return 'i2c:' + id + '/' + hex(addr)

class I2CSensor(Sensor):
    def __init__(self, name, i2c_addr, i2c_bus):
        super().__init__(url=i2c_url(i2c_bus.id, i2c_addr), name=name)
        self.i2c_address = i2c_addr
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
