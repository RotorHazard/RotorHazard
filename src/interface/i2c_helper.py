'''RotorHazard I2C interface layer.'''

import smbus # For i2c comms
import gevent
from gevent.lock import BoundedSemaphore # To limit i2c calls
import logging
from monotonic import monotonic

I2C_CHILL_TIME = 0.075 # Delay after i2c read/write

logger = logging.getLogger(__name__)


class I2CBus(object):
    def __init__(self):
        self.i2c = smbus.SMBus(1) # Start i2c bus
        self.semaphore = BoundedSemaphore(1) # Limits i2c to 1 read/write at a time
        self.i2c_timestamp = -1

    def i2c_end(self):
        self.i2c_timestamp = monotonic()

    def i2c_sleep(self):
        if self.i2c_timestamp == -1:
            return
        time_remaining = self.i2c_timestamp + I2C_CHILL_TIME - monotonic()
        if (time_remaining > 0):
            # print("i2c sleep {0}".format(time_remaining))
            gevent.sleep(time_remaining)

    def with_i2c(self, callback):
        val = None
        if callable(callback):
            with self.semaphore:
                self.i2c_sleep()
                val = callback()
                self.i2c_end()
        return val

    def with_i2c_quietly(self, callback):
        try:
            self.with_i2c(callback)
        except IOError as err:
            logger.info('I2C error: {0}'.format(err))
            self.i2c_end()


def create():
    return I2CBus()
