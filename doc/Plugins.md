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

*Actions* are behaviors be assigned to events by users from the server's UI. *Action effects* are assigned to and triggered by the *event* a user has configured within an *action*. All parameters of the selected *event* in the *action* become available to the *effect*.

*Effects* must be registered to be available in the UI. The `registerEffect` method of the `EventActions` object provides effect registration. Access to this method is provided though the `registerFn` argument of the `actionsInitialize` event. Pass an `ActionEffect` object to this method to register it.

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

#### ActionEffect(name, label, effectFn, fields)

Provides metadata and function linkage for *action effects*.

- `name` (string): internal identifier for this effect
- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `effectFn` (function): function to run when this effect is triggered
- `fields` (list): front-end fields to collect parameters from user interface

`fields` should be an array of dicts with the following format:
- `id` (string): internal identifier for this parameter
- `name` (string): user-facing text that appears in the RotorHazard frontend interface
- `type` (string): Currently accepts only "text"; additional options will become available in the future

Example:
```
ActionEffect(
    'udpmessage',
    'UDP Message',
    UDPMessageEffect,
    [
        {
            'id': 'text',
            'name': 'UDP message',
            'type': 'text',
        },
        {
            'id': 'ipaddress',
            'name': 'UDP IP Address',
            'type': 'text',
        },
        {
            'id': 'udpport',
            'name': 'UDP Port',
            'type': 'text',
        }
    ]
)
```

### LED Effects

*LED Effects* are colors and patterns that may be displayed by an LED strip (or panel) attached to the server. *Effects* are assigned by users in the server's UI, and triggered by the server when appropriate. Most *effects* are triggered by *standard events*, but some (such as the "idle" states) are unique to the LED system and not broadcast elsewhere. All parameters of the *event* become available to the *LED Effect*.

*Effects* must be registered to be available in the UI. The `registerEffect` method of the `LEDEventManager` object provides effect registration. Access to this method is provided though the `registerFn` argument of the `LED_Initialize` event. Pass an `LEDEffect` object to this method to register it.

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

#### LEDEffect(name, label, handlerFn, validEvents, [defaultArgs=None])

Provides metadata and function linkage for *LED effects*.

Often, `color` will be passed through as an argument, which is an RGB hexadecimal code that can be used to modify the effect's output as appropriate. For example, during the `RACE_LAP_RECORDED` event, color is often determined by the pilot that completed the lap.

- `name` (string): internal identifier for this effect
- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `handlerFn` (function): function to run when this effect is triggered
- `validEvents` (list): controls whether events can be assigned to various events
- `defaultargs` (dict): provides default arguments for the handler. These arguments will be overwritten if the `Event` provides arguments with the same keys.

By default, an *LED effect* will be available to all *events* that can produce LED output except *Evt.SHUTDOWN*, *LEDEvent.IDLE_DONE*, *LEDEvent.IDLE_RACING*, and *LEDEvent.IDLE_READY*. This can be modified with `validEvents`. It should contain a dict with the following optional keys. Each value should be a list of event identifiers.
- `exclude` (list): this *effect* will never be available for *events* specified here. As a special case, `Evt.ALL` will remove this *effect* from all *events* except those specifically included.
- `include` (list): this *effect* will always be available for *events* specified here  unless specifically excluded.
- `recommended` (list): *effects* in this list will receive priority ordering and visibility in the effect selection UI, at the top of the list, with an asterisk. `Evt.ALL` may be used here.

Normally when an *LED effect*'s handler function completes, the display system will look for a `time` argument and wait this many seconds before switching to an appropriate idle state. You can prevent switching to idle with the `preventIdle` argument, but usually it is more appropriate to set a reasonable `time`.

A list of standard and LED-specific *events* that will accept and trigger *effects* can be found in `src/server/led_event_manager.py`.

Be sure to `import gevent` and set `gevent.sleep` or `gevent.idle` frequently within your handler code. Failure to do this may delay or prevent server response while your handler is running.

Example:
```
LEDEffect(
    "bitmapRHLogo",
    "Image: RotorHazard",
    showBitmap,
    {
        'include': [Evt.SHUTDOWN],
        'recommended': [Evt.STARTUP]
    },
    {
        'bitmaps': 
            [
                {
                    "image": "static/image/LEDpanel-16x16-RotorHazard.png",
                    "delay": 0
                }
            ],
        'time': 60
    }
)
```

### Data Exporters

*Exporters* provide formatting of event data so it may be saved or sent elsewhere. A user may select and run an exporter from the UI, and will be provided with its contents in a file. Plugins may also trigger exports for their own purposes.

*Exporters* must be registered before use. The `registerExporter` method of the `DataExportManager` object provides effect registration. Access to this method is provided though the `registerFn` argument of the `Export_Initialize` event. Pass a `DataExporter` object to this method to register it.

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

#### DataExporter(name, label, formatterFn, assemblerFn)

Provides metadata and function linkage for *exporters*.

*Exporters* are run in two stages. First, the *assembler* pulls the data needed, then passes it to the *formatter*. In this way, a variety of *assemblers* can share a *formatter*, such as assembling pilot data, heat data, or race data and then passing it to be formatted as CSV or JSON.

- `name` (string): internal identifier for this effect
- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `formatterFn` (function): function to run for formatting stage
- `assemblerFn` (function): function to run for assembly stage

The `assemblerFn` receives (`RHData`, `PageCache`, `Language`) as arguments so that it may access and prepare timer data as needed.

The `formatterFn` receives the output of the `assemblerFn`.
