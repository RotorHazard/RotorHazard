"""Activate and manage connected LED displays via registered :class:`led_event_manager.LEDEffect`."""

_racecontext = None

@property
def enabled():
    """`Read Only` Returns True if LED system is enabled.

    :return: System is enabled
    :rtype: bool
    """
    return _racecontext.led_manager.isEnabled()

@property
def effects():
    """`Read Only` All registered LED effects.

    :return: List of :class:`led_event_manager.LEDEffects`
    :rtype: list[LEDEffects]
    """
    return _racecontext.led_manager.getRegisteredEffects()

def effect_by_event(event):
    """LED effect assigned to event. 

    :param event: Event to retrieve effect from
    :type event: str
    :return: Returns :class:`led_event_manager.LEDEffect` or None if event does not exist
    :rtype: LEDEffect|None
    """
    return _racecontext.led_manager.getEventEffect(event)

def effect_set(event, name):
    """Assign effect to event.

    :param event: Event to assign
    :type event: str
    :param name: Effect to assign to event
    :type name: str
    :return: Success value
    :rtype: bool
    """
    return _racecontext.led_manager.setEventEffect(event, name)

def clear():
    """Clears LEDs."""
    _racecontext.led_manager.clear()

def display_color(seat_index, from_result=False):
    """Color of seat in active race. 

    :param seat_index: Seat number
    :type seat_index: int
    :param from_result: True to use previously active (cached) race data, defaults to False
    :type from_result: bool, optional
    :return: :class:`Color` assigned to seat
    :rtype: Color
    """
    return _racecontext.led_manager.getDisplayColor(seat_index, from_result)

def activate_effect(args):
    """Immediately activate an LED effect. Should usually be called asynchronously with :meth:`gevent.spawn`.

    :param args: Must include `handler_fn` to activate; other arguments are passed to handler
    :type args: dict
    """
    _racecontext.led_manager.activateEffect(args)