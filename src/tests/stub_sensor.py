from sensors import Sensor, Reading

class StubSensor(Sensor):
    def __init__(self):
        Sensor.__init__(self, 'test:/test', 'TestSensor')
        self.description = 'Sensor for testing'
        self.value = 0

    @Reading(units='')
    def counter(self):
        return self.value

    @Reading(units='V')
    def voltage(self):
        return 12.8

    def update(self):
        self.value += 1


def discover(*args, **kwargs):
    return [StubSensor()]
