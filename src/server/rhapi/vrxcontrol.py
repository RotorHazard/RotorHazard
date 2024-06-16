"""View and manage connected Video Receiver devices.

Notice: The vrx control specification is expected to be modified in future versions. Please consider this while developing plugins.
"""

_racecontext = None

@property
def enabled():
    """`Read Only` Returns True if VRx control system is enabled

    :return: Control system is enabled
    :rtype: bool
    """
    return _racecontext.vrx_manager.isEnabled()

def kill():
    """Shuts down VRx control system.

    :return: _description_
    :rtype: _type_
    """
    return _racecontext.vrx_manager.kill()

@property
def status():
    """`Read Only` Returns status of VRx control system.

    :return: _description_
    :rtype: _type_
    """
    return _racecontext.vrx_manager.getControllerStatus()

@property
def devices():
    """`Read Only` Returns list of attached VRx control devices.

    :return: List of :class:`VRxControl.VRxController`
    :rtype: list[VRxController]
    """
    return _racecontext.vrx_manager.getDevices()

def devices_by_pilot(seat, pilot_id):
    """List VRx control deviced connected with a specific pilot.

    :param seat: Seat number
    :type seat: int
    :param pilot_id: ID of pilot
    :type pilot_id: int
    :return: Control deviced
    :rtype: VRxController
    """
    return _racecontext.vrx_manager.getActiveDevices(seat, pilot_id)
