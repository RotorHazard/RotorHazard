"""View registered :class:`Results.RaceClassRankMethod`."""

_racecontext = None

@property
def methods():
    """`Read Only` All registered class ranking methods.

    :return: A dictionary with the format {name : :class:`Results.RaceClassRankMethod`}
    :rtype: dict
    """
    return _racecontext.raceclass_rank_manager.methods