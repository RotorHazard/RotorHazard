"""View information provided by the harware interface layer."""

_racecontext = None

@property
def seats():
    """`Read Only` Hardware interface information.

    :return: List of interface information
    :rtype: list[Node]
    """
    return _racecontext.interface.nodes