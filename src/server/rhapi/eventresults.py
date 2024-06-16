"""View result data for all races, heats, classes, and event totals."""

_racecontext = None

@property
def results():
    """`Read Only` Calculated cumulative results.

    :return: Cumulative results
    :rtype: dict
    """
    return _racecontext.pagecache.get_cache()