"""Create and access new data structures"""

from RHUI import UIField

_racecontext = None

# Pilot Attribute
@property
def pilot_attributes():
    """`Read Only` Provides a list of registered pilot attributes

    :return: List of pilot attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.pilot_attributes

def register_pilot_attribute(field:UIField):
    """Register a pilot attribute to be displayed in the UI or otherwise made accessible to plugins.

    :param field: :class:`RHUI.UIField` to register
    :type field: UIField
    :return: List of Attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.register_pilot_attribute(field)

# Heat Attribute
@property
def heat_attributes():
    """`Read Only` Provides a list of registered heat attributes.

    :return: List of heat attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.heat_attributes

def register_heat_attribute(field:UIField):
    """Register a heat attribute to be made accessible to plugins.

    :param field: :class:`RHUI.UIField` to register
    :type field: UIField
    :return: List of Attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.register_heat_attribute(field)

# Race Class Attribute
@property
def raceclass_attributes():
    """`Read Only` Provides a list of registered race class attributes.

    :return: List of race class attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.raceclass_attributes

def register_raceclass_attribute(field:UIField):
    """Register a race class attribute to be made accessible to plugins.

    :param field: :class:`RHUI.UIField` to register
    :type field: UIField
    :return: List of Attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.register_raceclass_attribute(field)

# Race Attribute
@property
def race_attributes():
    """`Read Only` Provides a list of registered race attributes.

    :return: List of race attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.savedrace_attributes

def register_race_attribute(field:UIField):
    """Register a race attribute to be made accessible to plugins.

    :param field: :class:`RHUI.UIField` to register
    :type field: UIField
    :return: List of Attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.register_savedrace_attribute(field)

# Race Attribute
@property
def raceformat_attributes():
    """`Read Only` Provides a list of registered race format attributes.

    :return: List of race format attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.raceformat_attributes

def register_raceformat_attribute(field:UIField):
    """Register a race format attribute to be made accessible to plugins.

    :param field: :class:`RHUI.UIField` to register
    :type field: UIField
    :return: List of Attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.register_raceformat_attribute(field)

# General Setting
@property
def options():
    """`Read Only` Provides a list of registered options.

    :return: List of options
    :rtype: list[UIField]
    """
    return _racecontext.rhui.general_settings

def register_option(field:UIField, panel=None, order=0):
    """Register a option to be made accessible to plugins.

    :param field: :class:`RHUI.UIField` to register
    :type field: UIField
    :param panel: name of panel previously registered with ui.register_panel
    :type panel: str
    :param field: Attribute to register
    :type field: int
    :return: List of Attributes
    :rtype: list[UIField]
    """
    return _racecontext.rhui.register_general_setting(field, panel, order)