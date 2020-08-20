import sys

sys.path.append('../interface')

from sensor import Sensor

def discover():
    return [Sensor('TestSensor')]
