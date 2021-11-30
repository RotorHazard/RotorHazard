'''RotorHazard I2C interface layer.'''

try:
    from smbus2 import SMBus # For i2c comms
except:
    from smbus import SMBus
from . import i2c_url
import gevent.lock
import os
import logging
from monotonic import monotonic

I2C_CHILL_TIME = float(os.environ.get('RH_I2C_SLEEP', '0.015')) # Delay after i2c read/write

logger = logging.getLogger(__name__)


class I2CBus(object):
    def __init__(self, bus):
        self.id = bus
        self.i2c = SMBus(bus) # Start i2c bus
        self.i2c_rlock_obj = gevent.lock.RLock()  # for limiting i2c to 1 read/write at a time
        self.i2c_timestamp = -1

    def url_of(self, addr):
        return i2c_url(self.id, addr)

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
            with self.i2c_rlock_obj:
                self.i2c_sleep()
                try:
                    val = callback()
                finally:
                    self.i2c_end()
        return val

    def with_i2c_quietly(self, callback):
        try:
            self.with_i2c(callback)
        except IOError as err:
            logger.info('I2C error: {0}'.format(err))

    def close(self):
        pass


def create(rhconfig):
    bus_ids = rhconfig.HARDWARE['I2C_BUSES']
    buses = []
    for bus_id in bus_ids:
        logger.debug('Starting I2C on bus {0}'.format(bus_id))
        buses.append(I2CBus(bus_id))
    return buses
