"""Read and modify server configuration values."""

import copy

_racecontext = None

@property
def config():
    """`Read Only` _summary_

    :return: _description_
    :rtype: _type_
    """
    return copy.deepcopy(_racecontext.serverconfig.config)

def get_item(section, item, as_int=False):
    """_summary_

    :param section: _description_
    :type section: _type_
    :param item: _description_
    :type item: _type_
    :param as_int: _description_, defaults to False
    :type as_int: bool, optional
    :return: _description_
    :rtype: _type_
    """
    if as_int:
        return _racecontext.serverconfig.get_item_int(section, item)
    else:
        return _racecontext.serverconfig.get_item(section, item)

def set_item(section, item, value):
    """_summary_

    :param section: _description_
    :type section: _type_
    :param item: _description_
    :type item: _type_
    :param value: _description_
    :type value: _type_
    :return: _description_
    :rtype: _type_
    """
    return _racecontext.serverconfig.set_item(section, item, value)