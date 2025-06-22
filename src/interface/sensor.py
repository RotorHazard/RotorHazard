'''Sensor class for the hardware interface.'''

def Reading(units):
    def decorator(func):
        func.units = units
        return func
    return decorator

class Sensor:
    def __init__(self, name):
        self.name = name
        self.address = 0

    def getName(self):
        return self.name

    def getAddress(self):
        return self.address

    def getReadings(self):
        readings = {}
        for fname in dir(self):
            f = getattr(self, fname)
            if hasattr(f, 'units'):
                readings[f.__name__] = {'value': f(), 'units': f.units}
        return readings

    def update(self):
        pass

    def readData(self):
        return None

class I2CSensor(Sensor):
    @staticmethod
    def url(addr):
        return 'i2c:' + hex(addr)

    def __init__(self, name, i2c_helper):
        Sensor.__init__(self, name)
        self.i2c_helper = i2c_helper

    def update(self):
        self.i2c_helper.with_i2c_quietly(self.readData)
