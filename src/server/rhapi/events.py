"""Manage handlers for system events."""

import inspect
from eventmanager import Evt

_racecontext = None

def on(event, handler_fn, default_args=None, priority=None, unique=False, name=None):
    """_summary_

    :param event: _description_
    :type event: _type_
    :param handler_fn: _description_
    :type handler_fn: _type_
    :param default_args: _description_, defaults to None
    :type default_args: _type_, optional
    :param priority: _description_, defaults to None
    :type priority: _type_, optional
    :param unique: _description_, defaults to False
    :type unique: bool, optional
    :param name: _description_, defaults to None
    :type name: _type_, optional
    """
    if not priority:
        if event in [
                Evt.ACTIONS_INITIALIZE,
                Evt.CLASS_RANK_INITIALIZE,
                Evt.DATA_EXPORT_INITIALIZE,
                Evt.DATA_IMPORT_INITIALIZE,
                Evt.HEAT_GENERATOR_INITIALIZE,
                Evt.LED_INITIALIZE,
                Evt.POINTS_INITIALIZE,
                Evt.VRX_INITIALIZE,
            ]:
            priority = 75
        else:
            priority = 200

    if not name:
        name = inspect.getmodule(handler_fn).__name__

    _racecontext.events.on(event, name, handler_fn, default_args, priority, unique)

def off(event, name):
    """_summary_

    :param event: _description_
    :type event: _type_
    :param name: _description_
    :type name: _type_
    """
    _racecontext.events.off(event, name)

def trigger(event, args):
    """_summary_

    :param event: _description_
    :type event: _type_
    :param args: _description_
    :type args: _type_
    """
    _racecontext.events.trigger(event, args)