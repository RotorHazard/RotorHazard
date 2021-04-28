from sensors import Sensor, Reading

class StubSensor(Sensor):
    def __init__(self):
        Sensor.__init__(self, 'TestSensor')
        self.value = 0

    @Reading(units='')
    def counter(self):
        return self.value

    def update(self):
        self.value += 1

def discover(*args, **kwargs):
    return [StubSensor()]
