# Plugins

- [Installing and Running](#installing-and-running)
- [Development](#development)
    - [Initialize Function](#initialize-function)
    - [Standard Events](#standard-events)
    - [Actions](#actions)
    - [LED Effects](#led-effects)
    - [Data Exporters](#data-exporters)

## Installing and Running

RotorHazard makes use of externally loaded plugins to extend its functionality and behavior. Plugins are distributed as a directory (folder) containing an `__init__.py` file and potentially other files. Plugins are loaded during server startup. A line is added to the log for each plugin as it is found and imported; refer to the log to ensure plugins are being loaded as expected.

**To add and run a plugin, place the plugin's entire directoy in `/src/server/plugins`, and (re)start the server.**

If you have issues with a plugin, contact its developer to ensure compatibility with the version of RotorHazard you are running.

## Development

At minimum, a plugin must contain an `initialize()` function within its `__init__.py` file. From there, the plugin author can register *handlers* to various hooks within the system to run its code.

### Initialize Function

RotorHazard will call your plugin's `initialize()` function early during server startup. This function should not be used to add behaviors, but to register handlers where behavior will be applied. RotorHazard passes various utilities which may be of use in your plugin through named arguments.

- `Events` (EventManager): Allows registering *handlers* to *events* to run code at the appropriate times. See below for details.
- `__` (function): String localization function. Replaces strings with appropriate language alternate, if available.
- `SOCKET_IO` (SOCKET_IO): **Not supported.** Allows interfacing with the timer frontend's websocket implementation. *Will likely be replaced in a future version.*

For example, a controller for video receivers might register events like this:
```
def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on(Evt.RACE_STAGE, 'VRx', self.do_race_stage, {}, 75)
```

If you have code you would like run during startup, you may bind it to the `Evt.STARTUP` event.


### Standard Events

*Events* are *triggered* by the timer as important actions take place—for example, when a frequency is set, a pilot is added, or a race begins. When an *event* is *triggered*, all registered *handlers* are run. *Events* may pass arguments containing useful data such as the node number, pilot callsign, or race object.

Register a *handler* using the `.on()` function, usually within your `initialize()` function.

#### .on(event, name, handlerFn, [defaultArgs=None], [priority=200], [unique=False])

Registers a *handler* to an *event*. This causes the code in the *handler* to be run each time the *event* is *triggered* by any means (timer, plugin, or otherwise)

- `event` (string|Evt): the triggering *event* for this *handler*. A list of timer-provided events is contained within the `Evt` class in `/src/server/eventmanager.py`, which you can access in your plugin with `from eventmanager import Evt`. Custom events may also be created and triggered by plugins, allowing communication between them.
- `name` (string): a name for your handler. Only one handler with each name can be registered per *event*, so registering with the same `name` and `event` multiple times will cause handlers to be overridden. Choose something unique so as not to conflict with timer internals or other plugins.
- `handlerFn` (function): the function to run when this event triggers.
- `defaultArgs` (dict): provides default arguments for the handler. These arguments will be overwritten if the `Event` provides arguments with the same keys. 
- `priority` (int): determine the order handlers are run, lower numbers first. Priorities < 100 are executed synchronously, blocking other code from executing until they finish. Priorities >= 100 are executed asynchronously, allowing the timer to continue running other code. Handlers should generally be run asynchronously. As `gevents` are not true threads, be sure to `idle` or `sleep` your code at frequent intervals.
- `unique` (boolean): If run asynchronously (priority >= 100), a handler will cancel other handlers that have the same `name` (for example, only one LED effect can be visible at a time) Set to `True` to avoid this behavior regardless of handler `name` and run handlers to completion. Has no effect if `priority` < 100.

#### .off(event, name)

Removes a *handler* from an *event*. Removes only the specific `name` and `event` combination, so if you have registered the same `name` to multiple `events` and want to remove them all, you will need to do so individually.

- `event` (string|Evt): the triggering *event* for this *handler*.
- `name` (string): the registered `name` of the handler to remove.

#### .trigger(event, [evtArgs=None])

Triggers an *event*, causing all registered *handlers* to run

- `event` (string|Evt): the *event* to trigger
- `evtArgs` (dict): arguments to pass to the handler, overwriting matched keys in that handler's `defaultArgs`

### Actions

Actions are behaviors that can be assigned to events from the server's front-end interface, allowing users to customize when and how they occur.

Action effects are registered with the `actionsInitialize` event. This event provides a `registerFn` argument, which is a function that must be called to register your effects with the action system.

For example, an effect to send a UDP message might be registered with the following functions:
```
def registerHandlers(args):
    if 'registerFn' in args:
        for effect in discover():
            args['registerFn'](effect)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('actionsInitialize', 'action_UDP_message', registerHandlers, {}, 75, True)

def discover():
    return [
        ActionEffect( ... )
    ]
```

### LED Effects

LED effects are registered with the `LED_Initialize` event. This event provides a `registerFn` argument, which is a function that must be called to register your effects with the LED system.

For example, the bitmap display registers its effects with the following functions:
```
def registerHandlers(args):
    if 'registerFn' in args:
        for led_effect in discover():
            args['registerFn'](led_effect)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('LED_Initialize', 'LED_register_bitmap', registerHandlers, {}, 75)

def discover(*args, **kwargs):
    return [
        LEDEffect( ... ),
        LEDEffect( ... ),
        ...
    ]
```

### Data Exporters

Data exporters are registered with the `Export_Initialize` event. This event provides a `registerFn` argument, which is a function that must be called to register your effects with the data export system.

For example, the CSV exporter registers its options with the following functions:

```
def registerHandlers(args):
    if 'registerFn' in args:
        for exporter in discover():
            args['registerFn'](exporter)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('Export_Initialize', 'Export_register_CSV', registerHandlers, {}, 75)

def discover(*args, **kwargs):
    return [
        DataExporter( ... ),
        DataExporter( ... )
        ...
    ]
```