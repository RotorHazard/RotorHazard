# RHTimeFns:  Helpers for datetime and timezone functions.
#             Supports python 2 and python 3

from datetime import datetime

useTimezoneFlag = hasattr(datetime, "timezone")

def getEpochStartTime():
    if useTimezoneFlag:
        return datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    return datetime.utcfromtimestamp(0)

def getUtcDateTimeNow():
    if useTimezoneFlag:
        return datetime.now(datetime.timezone.utc)
    return datetime.utcnow()
