# RHTimeFns:  Helpers for datetime and timezone functions.

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
