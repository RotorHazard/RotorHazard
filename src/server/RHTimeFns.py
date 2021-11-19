# RHTimeFns:  Helpers for datetime and timezone functions.
#             Supports python 2 and python 3

from datetime import datetime
from monotonic import monotonic

useTimezoneFlag = hasattr(datetime, "timezone")


def getEpochStartTime():
    if useTimezoneFlag:
        return datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    return datetime.utcfromtimestamp(0)


def getUtcDateTimeNow():
    if useTimezoneFlag:
        return datetime.now(datetime.timezone.utc)
    return datetime.utcnow()


EPOCH_START = getEpochStartTime()


def getEpochTimeNow():
    '''
    Returns the current time in milliseconds since 1970-01-01.
    '''
    return int((getUtcDateTimeNow() - EPOCH_START).total_seconds() * 1000)


class MonotonicEpochSync:
    def __init__(self):
        epochTime = getEpochTimeNow() # ms
        monotonicTime = monotonic() # s
        # offset for converting 'monotonic' time to epoch milliseconds since 1970-01-01
        offset = epochTime - 1000.0*monotonicTime
        self.epochTime = epochTime
        self.monotonicTime = monotonicTime
        self.offset = offset

    def monotonic_to_epoch_millis(self, secs):
        '''
        Converts 'monotonic' time to epoch milliseconds since 1970-01-01.
        '''
        return round(1000.0*secs + self.offset)

    def diff(self, other):
        return self.epochTime - other.monotonic_to_epoch_millis(self.monotonicTime)

    def adjustBy(self, other, diff_ms):
        self.epochTime += diff_ms
        self.offset = other.offset
