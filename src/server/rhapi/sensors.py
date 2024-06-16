"""View data collected by environmental sensors such as temperature, voltage, and current."""

_racecontext = None

@property
def sensors_dict():
    """`Read Only` All sensor names and data.

    :return: dict of {name(string) : Sensor}
    :rtype: dict
    """
    return _racecontext.sensors.sensors_dict

@property
def sensor_names():
    """`Read Only` List of available sensors. 

    :return: List of sensors
    :rtype: list[string]
    """
    return list(_racecontext.sensors.sensors_dict.keys())

@property
def sensor_objs():
    """`Read Only` List of sensor data.

    :return: List of Sensor
    :rtype: list[Sensor]
    """
    return list(_racecontext.sensors.sensors_dict.values())

def sensor_obj(name):
    """Individual sensor data.

    :param name: Name of sensor to retrieve
    :type name: str
    :return: Sensor data
    :rtype: Sensor
    """
    return _racecontext.sensors.sensors_dict[name]