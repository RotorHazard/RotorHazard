"""Interact with RotorHazard's frontend user interface."""

from RHUtils import callWithDatabaseWrapper
_racecontext = None

@property
def panels():
    """`Read Only` The list of registered panels

    :return: A list of the discovered :class:`RHUI.UIPanel` objects
    :rtype: list[UIPanel]
    """
    return _racecontext.rhui.ui_panels

def register_panel(name, label, page, order=0):
    """The list of registered panels

    :param name: Internal identifier for this panel
    :type name: str
    :param label: Text used as visible panel header
    :type label: str
    :param page: Page to add panel to; one of "format", "settings"
    :type page: str
    :param order: Not yet implemented, defaults to 0
    :type order: int, optional

    :return: Returns all panels
    :rtype: list[UIPanel]
    """
    return _racecontext.rhui.register_ui_panel(name, label, page, order)

# Quick button
def register_quickbutton(panel, name, label, function, args=None):
    """Provides a simple interface to add a UI button and bind it to a function. Quickbuttons appear on assigned UI panels.

    :param panel: name of panel where button will appear
    :type panel: str
    :param name: Internal identifier for this quickbutton
    :type name: str
    :param label: Text used for visible button label
    :type label: str
    :param function: Function to run when button is pressed
    :type function: function
    :param args: Argument passed to function when called, defaults to None
    :type args: any, optional

    :return: _description_
    :rtype: _type_
    """
    return _racecontext.rhui.register_quickbutton(panel, name, label, function, args)

# Blueprint
def blueprint_add(blueprint):
    """Add custom pages to RotorHazard's frontend with Flask Blueprints.

    :param blueprint: _description_
    :type blueprint: Blueprint
    """
    _racecontext.rhui.add_blueprint(blueprint)

# Messaging
def message_speak(message):
    """Send a message which is parsed by the text-to-speech synthesizer.

    :param message: Text of message to be spoken
    :type message: str
    """
    _racecontext.rhui.emit_phonetic_text(message)

def message_notify(message):
    """Send a message which appears in the message center and notification bar.

    :param message: Text of message to display
    :type message: str
    """
    _racecontext.rhui.emit_priority_message(message, False)

def message_alert(message):
    """Send a message which appears as a pop-up alert.

    :param message: Text of message to display
    :type message: str
    """
    _racecontext.rhui.emit_priority_message(message, True)

def clear_messages(self):
    """_summary_
    """
    _racecontext.rhui.emit_clear_priority_messages()

# Socket
def socket_listen(message, handler):
    """Calls function when a socket event is received.

    :param message: Socket event name
    :type message: str
    :param handler: Function to call
    :type handler: function
    """
    _racecontext.rhui.socket_listen(message, handler)

def socket_send(message, data):
    """_summary_

    :param message: _description_
    :type message: _type_
    :param data: _description_
    :type data: _type_
    """
    _racecontext.rhui.socket_send(message, data)

def socket_broadcast(message, data):
    """_summary_

    :param message: _description_
    :type message: _type_
    :param data: _description_
    :type data: _type_
    """
    _racecontext.rhui.socket_broadcast(message, data)

# Broadcasts
@callWithDatabaseWrapper
def broadcast_ui(page):
    """Broadcast UI panel setup to all connected clients.

    :param page: Page to update
    :type page: str
    """
    _racecontext.rhui.emit_ui(page)

@callWithDatabaseWrapper
def broadcast_frequencies(self):
    """Broadcast seat frequencies to all connected clients.
    """
    _racecontext.rhui.emit_frequency_data()

@callWithDatabaseWrapper
def broadcast_pilots(self):
    """Broadcast pilot data to all connected clients.
    """
    _racecontext.rhui.emit_pilot_data()

@callWithDatabaseWrapper
def broadcast_heats(self):
    """Broadcast heat data to all connected clients.
    """
    _racecontext.rhui.emit_heat_data()

@callWithDatabaseWrapper
def broadcast_raceclasses(self):
    """Broadcast race class data to all connected clients.
    """
    _racecontext.rhui.emit_class_data()

@callWithDatabaseWrapper
def broadcast_raceformats(self):
    """Broadcast race format data to all connected clients.
    """
    _racecontext.rhui.emit_format_data()

@callWithDatabaseWrapper
def broadcast_current_heat(self):
    """Broadcast current heat selection to all connected clients.
    """
    _racecontext.rhui.emit_current_heat()

@callWithDatabaseWrapper
def broadcast_frequencyset(self):
    """Broadcast frequency set data to all connected clients.
    """
    _racecontext.rhui.emit_node_tuning()

@callWithDatabaseWrapper
def broadcast_race_status(self):
    """Broadcast race setup and status to all connected clients.
    """
    _racecontext.rhui.emit_race_status()