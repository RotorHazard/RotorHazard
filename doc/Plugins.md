# Plugins

- [Installing and Running](#installing-and-running)
- [Development](#development)
    - [Initialize Function](#initialize-function)
    - [Standard Events](#standard-events)
    - [Race Points](#race-points)
    - [Class Ranking](#class-ranking)
    - [Heat Generators](#heat-generators)
    - [Actions](#actions)
    - [LED Effects](#led-effects)
    - [Data Exporters](#data-exporters)
    - [Data Importers](#data-importers)
    - [UI Fields](#ui-fields)

## Installing and Running

**To add and run a plugin, place the plugin's entire directory in `/src/server/plugins`, and (re)start the server.**

RotorHazard makes use of externally loaded plugins to extend its functionality and behavior. Plugins are distributed as a directory (folder) containing an `__init__.py` file and potentially other files. Plugins are loaded during server startup. A line is added to the log for each plugin as it is found and imported; refer to the log to ensure plugins are being loaded as expected.

If you have issues with a plugin, contact its developer to ensure compatibility with the version of RotorHazard you are running.

## Development

At minimum, a plugin must contain an `initialize()` function within its `__init__.py` file. From there, the plugin author has a lot of freedom to work with RotorHazard's internal functions and data. Plugins can register *handlers* to various hooks within the system to run its code.

### Initialize Function

RotorHazard calls a plugin's `initialize()` function early during server startup. This function should not be used to add behaviors, but to register handlers where behavior will be applied. RotorHazard passes various utilities which may be of use in your plugin through named arguments.

- `events` (EventManager): Allows registering *handlers* to *events* to run code at the appropriate times. See [Standard Events](#standard-events)
- `rhapi` (RHAPI): Allows interfacing with the timer's API for working with data and frontend UI. See [RHAPI](RHAPI.md)

For example, a controller for actions might register events like this:
```
from eventmanager import Evt

def initialize(**kwargs):
    if 'events' in kwargs:
        kwargs['events'].on(Evt.ACTIONS_INITIALIZE, 'action_builtin', register_handlers, {}, 75)
```

If you have code you would like run during startup, you may bind it to the `Evt.STARTUP` event.


### RHAPI

`RHAPI` provides a wide range of properties and methods across RotorHazard's internal systems. Using RHAPI, one can manipulate nearly every facet of a race event and RotorHazard's behavior.

See [RHAPI Documentation](RHAPI.md)

### Standard Events

*Events* are *triggered* by the timer as important actions take place—for example, when a frequency is set, a pilot is added, or a race begins. When an *event* is *triggered*, all registered *handlers* are run. *Events* may pass arguments containing useful data such as the node number, pilot callsign, or race object.

Register a *handler* using the `.on()` function, usually within your `initialize()` function.

#### .on(event, name, handler_fn, default_args=None, priority=200, unique=False)

Registers a *handler* to an *event*. This causes the code in the *handler* to be run each time the *event* is *triggered* by any means (timer, plugin, or otherwise)

- `event` (string|Evt): the triggering *event* for this *handler*. A list of timer-provided events is contained within the `Evt` class in `/src/server/eventmanager.py`, which you can access in your plugin with `from eventmanager import Evt`. Custom events may also be created and triggered by plugins, allowing communication between them.
- `name` (string): a name for your handler. Only one handler with each name can be registered per *event*, so registering with the same `name` and `event` multiple times will cause handlers to be overridden. Choose something unique so as not to conflict with timer internals or other plugins.
- `handler_fn` (function): the function to run when this event triggers.
- `default_args` (dict): provides default arguments for the handler. These arguments will be overwritten if the `Event` provides arguments with the same keys. 
- `priority` (int): determine the order handlers are run, lower numbers first. Priorities < 100 are executed synchronously, blocking other code from executing until they finish. Priorities >= 100 are executed asynchronously, allowing the timer to continue running other code. Handlers should generally be run asynchronously, except initial registrations. As `gevents` are not true threads, be sure to `idle` or `sleep` your code at frequent intervals.
- `unique` (boolean): If run asynchronously (priority >= 100), a handler will cancel other handlers that have the same `name` (for example, only one LED effect can be visible at a time) Set to `True` to avoid this behavior regardless of handler `name` and run handlers to completion. Has no effect if `priority` < 100.

#### .off(event, name)

Removes a *handler* from an *event*. Removes only the specific `name` and `event` combination, so if you have registered the same `name` to multiple `events` and want to remove them all, you will need to do so individually.

- `event` (string|Evt): the triggering *event* for this *handler*.
- `name` (string): the registered `name` of the handler to remove.

#### .trigger(event, evtArgs=None)

Triggers an *event*, causing all registered *handlers* to run

- `event` (string|Evt): the *event* to trigger
- `evtArgs` (dict): arguments to pass to the handler, overwriting matched keys in that handler's `default_args`


### Race Points

*Points Methods* are functions that assign point values to pilot results when a race is completed. If a user assigns a points method to a race format, points will be displayed on the race and heat summary leaderboards. Points may also be used and displayed by *Class Ranking Methods*.

*Points Methods* must be registered to be available in the UI. Access to registration is provided though the `register_fn` argument of the `Evt.POINTS_INITIALIZE` event. Pass a `RacePointsMethod` object to this method to register it.

For example, an effect to score points corresponding to position might be registered with the following functions:
```
from eventmanager import Evt
from Results import RacePointsMethod

def register_handlers(args):
    if 'register_fn' in args:
        for method in discover():
            args['register_fn'](method)

def initialize(**kwargs):
    if 'events' in kwargs:
        kwargs['events'].on(Evt.POINTS_INITIALIZE, 'points_register_byrank', register_handlers, {}, 75)

def discover():
    return [
        RacePointsMethod( ... )
    ]
```

#### RacePointsMethod(name, label, assign_fn, default_args=None, settings=None)

Provides metadata and function linkage for *points methods*.

- `name` (string): internal identifier for this method
- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `assign_fn` (function): function to run when points are calculated for a race
- `default_args` _optional_ (dict): arguments passed to the `assignFn` when run, unless overridden by local arguments
- `settings` _optional_ (list\[UIField\]): A list of paramters to provide to the user; see [UI Fields](#ui-fields)

The `assignFn` receives as arguments:

- `rhapi` (RHAPI): the RHAPI class
- `leaderboard` (dict): full race leaderboard
- `args` (dict): collated default and locally-provided arguments

`assign_fn` must return a modified leaderboard dict where the "primary leaderboard" includes a `points` key with appropriate values assigned. The "primary leaderboard" is a dict at the root level of the full leaderboard, and will be identified in the `meta` dict with the `primary_leaderboard` key.

### Class Ranking

*Class Ranking Methods* are functions that output custom leaderboards to class results after races are completed. If a user assigns a ranking method to a class, the cooresponding leaderboard will be displayed as a "Class Ranking" panel.

*Class Ranking Methods* must be registered to be available in the UI. Access to registration is provided though the `register_fn` argument of the `Evt.CLASS_RANK_INITIALIZE` event. Pass a `RaceClassRankMethod` object to this method to register it.

For example, an effect to rank based on the best X rounds might be registered with the following functions:
```
from eventmanager import Evt
from Results import RaceClassRankMethod

def register_handlers(args):
    if 'register_fn' in args:
        for method in discover():
            args['register_fn'](method)

def initialize(**kwargs):
    if 'events' in kwargs:
        kwargs['events'].on(Evt.CLASS_RANK_INITIALIZE, 'classrank_register_bestx', register_handlers, {}, 75)

def discover():
    return [
        RaceClassRankMethod( ... )
    ]
```

#### RaceClassRankMethod(name, label, rank_fn, default_args=None, settings=None)

Provides metadata and function linkage for *points methods*.

- `name` (string): internal identifier for this method
- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `rank_fn` (function): function to run when class leaderboards are calculated
- `default_args` _optional_ (dict): arguments passed to the `rank_fn` when run, unless overridden by local arguments
- `settings` _optional_ (list\[UIField\]): A list of paramters to provide to the user; see [UI Fields](#ui-fields)

The `rank_fn` receives as arguments:

- `rhapi` (RHAPI): the RHAPI class
- `race_class` (dict): current `RaceClass` object
- `args` (dict): collated default and locally-provided arguments

`rank_fn` must return a tuple of (`leaderboard`, `meta`). `leaderboard` is a list of dicts with `position` and any other keys the author deems necessary, and should be ordered by `position`. `meta` is a dict with the following format:

- `rank_fields` (list): A list of dicts with the following format:
    - `name` (string): the key of the field in `leaderboard` with data to display
    - `label` (string): user-facing text used as column header in the ranking table

When displayed on the front-end, only `position` and fields listed in `rank_fields` will be displayed in the ranking table.


### Heat Generators

*Heat Generators* are functions that return a list of heats which are fed into a race class. When a user runs a generator, they choose a source for seeding and feed the results into an existing class or create a new class.

*HeatGenerators* must be registered to be available in the UI. Access to registration is provided though the `register_fn` argument of the `Evt.HEAT_GENERATOR_INITIALIZE` event. Pass a `HeatGenerator` object to this method to register it.

For example, a generator to create ladders might be registered with the following functions:
```
from eventmanager import Evt
from HeatGenerator import HeatGenerator, HeatPlan, HeatPlanSlot, SeedMethod

def register_handlers(args):
    if 'register_fn' in args:
        for generator in discover():
            args['register_fn'](generator)

def initialize(**kwargs):
    if 'events' in kwargs:
        kwargs['events'].on(Evt.HEAT_GENERATOR_INITIALIZE, 'HeatGenerator_register_ladder', register_handlers, {}, 75)

def discover():
    return [
        HeatGenerator( ... )
    ]
```

#### HeatGenerator (name, label, generator_fn, default_args=None, settings=None)

- `name` (string): internal identifier for this generator
- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `generator_fn` (function): function to run when generator is invoked
- `default_args` _optional_ (dict): arguments passed to the `generator_fn` when run, unless overridden by local arguments
- `settings` _optional_ (list\[UIField\]): A list of paramters to provide to the user; see [UI Fields](#ui-fields)

The `generator_fn` receives as arguments:

- `rhapi` (RHAPI): the RHAPI class
- `args` (dict): collated default and locally-provided arguments

`args` will include, at minimum:
- `input_class` (int): id of race class intended to be used for seeding
- `output_class` (int or None): id of race class where generated heats will be output
- `available_seats` (int): number of seats currently available to assign pilots into (seats with an active frequency assignment)

Your `generator_fn` must return a list of `HeatPlan`s (or `None`). 

A `HeatPlan` object uses the following format:
- `name` (string): Name to be applied to this heat
- `slots` (list\[HeatPlanSlot\]): A list of `HeatPlanSlot`s

A `HeatPlanSlot` object uses the following format:
    - `method` (SeedMethod): Method used for seeding
    - `seed_rank` (int): Rank to seed from
    - `seed_index` _optional_ (int): Index of heat within the plan list to seed from, when `method` is `HEAT_INDEX`

##### Seeding methods
Heat slots can be seeded either directly from
`SeedMethod` (imported from `HeatGenerator`)

- `INPUT`: The slot is seeded from the `seed_rank` position in the input class ranking
- `HEAT_INDEX`: The slot is seeded from the `seed_rank` position in the heat specified by `seed_index`

The following heat plan is a double-advance ladder. Pilots ranked 3rd through 6th from the input class are seeded into the first heat. Then, the 1st and 2nd place from that heat advance to the second heat where they join the 1st and 2nd place from the input class.
```
[
    HeatPlan(
        "B Main",
        [
            HeatPlanSlot(SeedMethod.INPUT, 3),
            HeatPlanSlot(SeedMethod.INPUT, 4),
            HeatPlanSlot(SeedMethod.INPUT, 5),
            HeatPlanSlot(SeedMethod.INPUT, 6)
        ]
    ),
    HeatPlan(
        "A Main",
        [
            HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
            HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
            HeatPlanSlot(SeedMethod.INPUT, 1),
            HeatPlanSlot(SeedMethod.INPUT, 2)
        ]
    )
]
```


### Actions

*Actions* are behaviors assigned to events by users from the server's UI. *Action effects* are assigned to and triggered by the *event* a user has configured within an *action*. All parameters of the selected *event* in the *action* become available to the *effect*.

*Effects* must be registered to be available in the UI. Access to registration is provided though the `register_fn` argument of the `Evt.ACTIONS_INITIALIZE` event. Pass an `ActionEffect` object to this method to register it.

For example, an effect to send a UDP message might be registered with the following functions:
```
from eventmanager import Evt
from EventActions import ActionEffect

def register_handlers(args):
    if 'register_fn' in args:
        for effect in discover():
            args['register_fn'](effect)

def initialize(**kwargs):
    if 'events' in kwargs:
        kwargs['events'].on(Evt.ACTIONS_INITIALIZE, 'action_UDP_message', register_handlers, {}, 75)

def discover():
    return [
        ActionEffect( ... )
    ]
```

#### ActionEffect(name, label, effect_fn, fields)

Provides metadata and function linkage for *action effects*.

- `name` (string): internal identifier for this effect
- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `effect_fn` (function): function to run when this effect is triggered
- `fields` _optional_ (list\[UIField\]): A list of paramters to provide to the user; see [UI Fields](#ui-fields)

Example:
```
ActionEffect(
    'udpmessage',
    'UDP Message',
    UDP_message_effect,
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

*Effects* must be registered to be available in the UI. Access to registration is provided though the `register_fn` argument of the `Evt.LED_INITIALIZE` event. Pass an `LEDEffect` object to this method to register it.

For example, the bitmap display registers its effects with the following functions:
```
from eventmanager import Evt
from led_event_manager import LEDEffect

def register_handlers(args):
    if 'register_fn' in args:
        for led_effect in discover():
            args['register_fn'](led_effect)

def initialize(**kwargs):
    if 'events' in kwargs:
        kwargs['events'].on(Evt.LED_INITIALIZE, 'LED_register_bitmap', register_handlers, {}, 75)

def discover(*args, **kwargs):
    return [
        LEDEffect( ... ),
        LEDEffect( ... ),
        ...
    ]
```

#### LEDEffect(name, label, handler_fn, valid_events, [default_args=None])

Provides metadata and function linkage for *LED effects*.

Often, `color` will be passed through as an argument, which is an RGB hexadecimal code that can be used to modify the effect's output as appropriate. For example, during the `RACE_LAP_RECORDED` event, color is often determined by the pilot that completed the lap.

- `name` (string): internal identifier for this effect
- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `handler_fn` (function): function to run when this effect is triggered
- `valid_events` (list): controls whether events can be assigned to various events
- `default_args` _optional_ (dict): provides default arguments for the handler. These arguments will be overwritten if the `Event` provides arguments with the same keys.

By default, an *LED effect* will be available to all *events* that can produce LED output except *Evt.SHUTDOWN*, *LEDEvent.IDLE_DONE*, *LEDEvent.IDLE_RACING*, and *LEDEvent.IDLE_READY*. This can be modified with `valid_events`. It should contain a dict with the following optional keys. Each value should be a list of event identifiers.
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
    show_bitmap,
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

*Exporters* must be registered before use. Access to registration is provided though the `register_fn` argument of the `Evt.DATA_EXPORT_INITIALIZE` event. Pass a `DataExporter` object to this method to register it.

For example, a plugin can register exporters with the following functions:

```
from eventmanager import Evt
from data_export import DataExporter

def register_handlers(args):
    if 'register_fn' in args:
        for exporter in discover():
            args['register_fn'](exporter)

def initialize(**kwargs):
    if 'events' in kwargs:
        kwargs['events'].on(Evt.DATA_EXPORT_INITIALIZE, 'export_register_myplugin', register_handlers, {}, 75)

def discover(*args, **kwargs):
    return [
        DataExporter( ... ),
        DataExporter( ... )
        ...
    ]
```

#### DataExporter(name, label, formatter_fn, assembler_fn)

Provides metadata and function linkage for *exporters*.

*Exporters* are run in two stages. First, the *assembler* pulls the data needed, then passes it to the *formatter*. In this way, a variety of *assemblers* can share a *formatter*, such as assembling pilot data, heat data, or race data and then passing it to be formatted as CSV or JSON.

- `name` (string): internal identifier for this effect
- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `formatter_fn` (function): function to run for formatting stage
- `assembler_fn` (function): function to run for assembly stage

The `assembler_fn` receives `rhapi` as an argument so that it may access and prepare timer data as needed.

The `formatter_fn` receives the output of the `assembler_fn`.


### Data Importers

*Importers* accept data and process it so that it can be added to the RH database. A user may select and run an importer from the UI, with a file selector as input. Plugins may also trigger imports for their own purposes.

*Importers* must be registered before use. Access to registration is provided though the `register_fn` argument of the `Evt.DATA_IMPORT_INITIALIZE` event. Pass a `DataImporter` object to this method to register it.

For example, a plugin can register importers with the following functions:

```
from eventmanager import Evt
from data_import import DataImporter

def register_handlers(args):
    if 'register_fn' in args:
        for importer in discover():
            args['register_fn'](importer)

def initialize(**kwargs):
    if 'events' in kwargs:
        kwargs['events'].on(Evt.DATA_IMPORT_INITIALIZE, 'import_register_myplugin', register_handlers, {}, 75)

def discover(*_args, **_kwargs):
    # returns array of exporters with default arguments, fields
    return [
        DataImporter( ... ),
        ...
    ]
```

#### DataImporter(name, label, import_fn, default_args=None, settings=None)

Provides metadata and function linkage for *importers*.

When an importer is run, the `run_import` method is called, which collates default and locally-provided arguments, then calls the `import_fn`. 

- `name` (string): internal identifier for this effect
- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `import_fn` (function): function to run for formatting stage
- `default_args` _optional_ (dict): arguments passed to the `import_fn` when run, unless overridden by local arguments
- `settings` _optional_ (list\[UIField\]): A list of paramters to provide to the user; see [UI Fields](#ui-fields)

The `import_fn` receives as arguments:

- `rhapi` (RHAPI): the RHAPI class
- `data` (any): data to import, provided by the user
- `args` (dict): collated default and locally-provided arguments


### UI Fields

An `RHUI.UIField` object defines a frontend user interface for collecting data. It is defined in the following format:
- `name` (string): internal identifier for this parameter
- `label` (string): text that appears in the RotorHazard frontend interface
- `desc` _optional_ (string): additional user-facing text that appears in the RotorHazard frontend interface describing notes or special instructions for use
- `field_type` (UIFieldType): One of `UIFieldType.TEXT`, `UIFieldType.BASIC_INT`, `UIFieldType.SELECT`, or `UIFieldType.CHECKBOX`
- `value` _optional_ (any): Default value for field

If `field_type` is `TEXT`

- `placeholder` _optional_ (string): Text displayed when no value is present

If `field_type` is `BASIC_INT`

- `placeholder` _optional_ (string): Text displayed when no value is present

If `field_type` is `CHECKBOX`

- `value` is boolean and no longer optional

If `field_type` is `SELECT`

- `options` (list\[UIFieldSelectOption\]): a list of `UIFieldSelectOption` objects with the following properties:
    - `value` (string): internal identifier used when this option is selected
    - `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `value` is no longer optional and must match the `value` of an item in `options`.

Import UI Fields objects from RHUI.

```
from RHUI import UIField, UIFieldType, UIFieldSelectOption
```
