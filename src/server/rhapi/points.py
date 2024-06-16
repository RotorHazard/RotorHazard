"""View registered :class:`Results.RacePointsMethod`."""

_racecontext = None

@property
def methods():
    """`Read Only` All registered class ranking methods.

    :return: A dictionary with the format {name : :class:`Results.RacePointsMethod`}
    :rtype: dict
    """
    return _racecontext.race_points_manager.methods