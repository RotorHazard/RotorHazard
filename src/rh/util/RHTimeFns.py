# RHTimeFns:  Helpers for datetime and timezone functions.

from datetime import datetime, timedelta, timezone
from . import ms_counter


def getEpochStartTime():
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def getUtcDateTimeNow():
    return datetime.now(timezone.utc)


EPOCH_START = getEpochStartTime()


def getEpochTimeNow():
    '''
    Returns the current time in milliseconds since 1970-01-01.
    '''
    td = getUtcDateTimeNow() - EPOCH_START
    return round(td/timedelta(milliseconds=1))


class MonotonicEpochSync:
    def __init__(self):
        epochTime_ms = getEpochTimeNow()
        monotonicTime_ms = ms_counter()
        # offset for converting 'monotonic' time to epoch milliseconds since 1970-01-01
        offset_ms = epochTime_ms - monotonicTime_ms
        self.epoch_ms = epochTime_ms
        self.monotonic_ms = monotonicTime_ms
        self.offset_ms = offset_ms

    def monotonic_to_epoch_millis(self, clock_ms: int) -> int:
        '''
        Converts millisecond 'monotonic' time to epoch milliseconds since 1970-01-01.
        '''
        return clock_ms + self.offset_ms

    def diff(self, other):
        return self.epoch_ms - other.monotonic_to_epoch_millis(self.monotonic_ms)

    def adjustBy(self, other, diff_ms):
        self.epoch_ms += diff_ms
        self.offset_ms = other.offset_ms
