# Plugins

- [Installing and Running](#installing-and-running)
- [Development](#development)
    - [Initialize Function](#initialize-function)
    - [RHAPI](#rhapi)
    - [Standard Events](#standard-events)
    - [Race Points](#race-points)
    - [Class Ranking](#class-ranking)
    - [Heat Generators](#heat-generators)
    - [Actions](#actions)
    - [LED Effects](#led-effects)
    - [Data Exporters](#data-exporters)
    - [Data Importers](#data-importers)
    - [UI Fields](#ui-fields)
    - [Metadata](#metadata)

## Installing and Running

**To add and run a plugin, place the plugin's entire directory in `/src/server/plugins`, and (re)start the server.**

RotorHazard makes use of externally loaded plugins to extend its functionality and behavior. Plugins are distributed as a directory (folder) containing an `__init__.py` file and potentially other files. Plugins are loaded during server startup. A line is added to the log for each plugin as it is found and imported; refer to the log to ensure plugins are being loaded as expected.

If you have issues with a plugin, contact its developer to ensure compatibility with the version of RotorHazard you are running.

## Development

At minimum, a plugin must contain an `initialize()` function within its `__init__.py` file. A plugin may assign functions to *standard events* or register *handlers* to various hooks within the system to run its code.

### Initialize Function

RotorHazard calls a plugin's `initialize()` function early during server startup. _This function should not be used to add behaviors directly_, but to register handlers where behavior will be called. As the only argument to `initialize`, RotorHazard provides the timer's API for working with data and frontend UI; see [RHAPI](RHAPI.md).

For example, a plugin might register events to be run at startup like this:
```
from eventmanager import Evt

def initialize(rhapi):
    rhapi.events.on(Evt.STARTUP, my_startup_function)
```

### RHAPI

`RHAPI` provides a wide range of properties and methods across RotorHazard's internal systems. Using RHAPI, one can manipulate nearly every facet of a race event and RotorHazard's behavior.

See [RHAPI Documentation](RHAPI.md)

### Standard Events

*Events* are *triggered* by the timer as important actions take place—for example, when a frequency is set, a pilot is added, or a race begins. When an *event* is *triggered*, all registered *handlers* are run. *Events* may pass arguments containing useful data such as the node number, pilot callsign, or race object. 

Interfacing with *Events* is provided via [RHAPI](RHAPI.md#standard-events).


### Race Points

*Points Methods* are functions that assign point values to pilot results when a race is completed. If a user assigns a points method to a race format, points will be displayed on the race and heat summary leaderboards. Points may also be used and displayed by *Class Ranking Methods*.

*Points Methods* must be registered to be available in the UI. Access to registration is provided though the `register_fn` argument of the `Evt.POINTS_INITIALIZE` event. Pass a `RacePointsMethod` object to this method to register it.

For example, a points method might be registered with the following functions:
```
from eventmanager import Evt
from Results import RacePointsMethod

def my_points_method_fn(rhapi, leaderboard, args):
    ...

def register_handlers(args):
    args['register_fn'](
        RacePointsMethod("My Points Method", my_points_method_fn)
    )

def initialize(rhapi):
    rhapi.events.on(Evt.POINTS_INITIALIZE, register_handlers)
```

#### RacePointsMethod(label, assign_fn, default_args=None, settings=None, name=None)

Provides metadata and function linkage for *points methods*.

- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `assign_fn` (function): function to run when points are calculated for a race
- `default_args` _optional_ (dict): arguments passed to the `assign_fn` when run, unless overridden by local arguments
- `settings` _optional_ (list\[UIField\]): A list of paramters to provide to the user; see [UI Fields](#ui-fields)
- `name` _optional_ (string): internal identifier (auto-generated from `label` if not provided)

The `assignFn` receives as arguments:

- `rhapi` (RHAPI): the RHAPI class
- `leaderboard` (dict): full race leaderboard
- `args` (dict): collated default and locally-provided arguments

`assign_fn` must return a modified leaderboard dict where the "primary leaderboard" includes a `points` key with appropriate values assigned. The "primary leaderboard" is a dict at the root level of the full leaderboard, and will be identified in the `meta` dict with the `primary_leaderboard` key.

### Class Ranking

*Class Ranking Methods* are functions that output custom leaderboards to class results after races are completed. If a user assigns a ranking method to a class, the cooresponding leaderboard will be displayed as a "Class Ranking" panel.

*Class Ranking Methods* must be registered to be available in the UI. Access to registration is provided though the `register_fn` argument of the `Evt.CLASS_RANK_INITIALIZE` event. Pass a `RaceClassRankMethod` object to this method to register it.

For example, a class rank might be registered with the following functions:
```
from eventmanager import Evt
from Results import RaceClassRankMethod

def my_class_rank_fn(rhapi, race_class, args):
    ...

def register_handlers(args):
    args['register_fn'](
        RaceClassRankMethod("My Class Ranking", my_class_rank_fn)
    )

def initialize(rhapi):
    rhapi.events.on(Evt.CLASS_RANK_INITIALIZE, register_handlers)
```

#### RaceClassRankMethod(label, rank_fn, default_args=None, settings=None, name=None)

Provides metadata and function linkage for *points methods*.

- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `rank_fn` (function): function to run when class leaderboards are calculated
- `default_args` _optional_ (dict): arguments passed to the `rank_fn` when run, unless overridden by local arguments
- `settings` _optional_ (list\[UIField\]): A list of paramters to provide to the user; see [UI Fields](#ui-fields)
- `name` _optional_ (string): internal identifier (auto-generated from `label` if not provided)

The `rank_fn` receives as arguments:

- `rhapi` (RHAPI): the RHAPI class
- `race_class` (dict): current `RaceClass` object
- `args` (dict): collated default and locally-provided arguments

`rank_fn` must return a tuple of (`leaderboard`, `meta`). 

`leaderboard` is a table&#8212;functionally, a list of dicts&#8212;that should be ordered by ranking. The "row" dicts must contain:

- `position` (string): The rank for this row; not required to be unique or numeric
- `pilot_id` (int): ID value for the pilot in this row 
- `callsign` (string): callsing for the pilot in this row

The row dicts may additionally contain any other keys the author deems necessary, but all rows in the table must maintain the same structure.

`meta` is a dict with the following format:

- `method_label` _optional_ (string): User-facing rank title (for Results page)
- `rank_fields` (list): A list of dicts with the following format:
    - `name` (string): the key of the field in `leaderboard` with data to display
    - `label` (string): user-facing text used as column header in the ranking table

When displayed on the front-end, only `position`, `callsign` and fields listed in `rank_fields` will be displayed in the ranking table.


### Heat Generators

*Heat Generators* are functions that return a list of heats which are fed into a race class. When a user runs a generator, they choose a source for seeding and feed the results into an existing class or create a new class.

*HeatGenerators* must be registered to be available in the UI. Access to registration is provided though the `register_fn` argument of the `Evt.HEAT_GENERATOR_INITIALIZE` event. Pass a `HeatGenerator` object to this method to register it.

For example, a heat generator might be registered with the following functions:
```
from eventmanager import Evt
from HeatGenerator import HeatGenerator, HeatPlan, HeatPlanSlot, SeedMethod

def my_heat_generator_fn(rhapi, args):
    ...

def register_handlers(args):
    args['register_fn'](
        HeatGenerator("My Generator", my_heat_generator_fn)
    )

def initialize(rhapi):
    rhapi.events.on(Evt.HEAT_GENERATOR_INITIALIZE, register_handlers)
```

#### HeatGenerator (label, generator_fn, default_args=None, settings=None, name=None)

- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `generator_fn` (function): function to run when generator is invoked
- `default_args` _optional_ (dict): arguments passed to the `generator_fn` when run, unless overridden by local arguments
- `settings` _optional_ (list\[UIField\]): A list of paramters to provide to the user; see [UI Fields](#ui-fields)
- `name` _optional_ (string): internal identifier (auto-generated from `label` if not provided)

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
    - `seed_index` _optional_ (int): Index of heat within the plan list to seed from, when `method` is `HEAT_INDEX` or `CLASS_INDEX`

##### Seeding methods
Heat slots can be seeded either directly from
`SeedMethod` (imported from `HeatGenerator`)

- `INPUT`: The slot is seeded from the `seed_rank` position in the input class ranking
- `HEAT_INDEX`: The slot is seeded from the `seed_rank` position in the heat specified by `seed_index`
- `CLASS_INDEX`: The slot is seeded from the `seed_rank` position in the class specified by `seed_index`

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

For example, an effect might be registered with the following functions:
```
from eventmanager import Evt
from EventActions import ActionEffect

def my_actions_fn(action, args):
    ...

def register_handlers(args):
    args['register_fn'](
        ActionEffect("My Action", my_actions_fn)
    )

def initialize(rhapi):
    rhapi.events.on(Evt.ACTIONS_INITIALIZE, register_handlers)
```

#### ActionEffect(label, effect_fn, fields, name=None)

Provides metadata and function linkage for *action effects*.

- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `effect_fn` (function): function to run when this effect is triggered
- `fields` _optional_ (list\[UIField\]): A list of paramters to provide to the user; see [UI Fields](#ui-fields)
- `name` _optional_ (string): internal identifier (auto-generated from `label` if not provided)

Example:
```
ActionEffect(
    'udpmessage',
    'UDP Message',
    UDP_message_effect,
    [
        UIField('text', "UDP message", UIFieldType.TEXT),
        UIField('ipaddress', "UDP IP Address", UIFieldType.TEXT),
        UIField('udpport', "UDP Port", UIFieldType.TEXT),
    ]
)
```


### LED Effects

*LED Effects* are colors and patterns that may be displayed by an LED strip (or panel) attached to the server. *Effects* are assigned by users in the server's UI, and triggered by the server when appropriate. Most *effects* are triggered by *standard events*, but some (such as the "idle" states) are unique to the LED system and not broadcast elsewhere. All parameters of the *event* become available to the *LED Effect*.

*Effects* must be registered to be available in the UI. Access to registration is provided though the `register_fn` argument of the `Evt.LED_INITIALIZE` event. Pass an `LEDEffect` object to this method to register it.

For example, an LED effect might be registered with the following functions:
```
from eventmanager import Evt
from led_event_manager import LEDEffect, effect_delay

def my_led_effect(args):
    ...

def register_handlers(args):
    args['register_fn'](
        LEDEffect("Image: RotorHazard", my_led_effect, {}),
    )

def initialize(rhapi):
    rhapi.events.on(Evt.LED_INITIALIZE, register_handlers)
```

Effects run as IDLE do not clear the display when they complete.

LED effects which contain animation require execution delays. Effects **MUST** use the provided `effect_delay` for this purpose _(see below)_.

> [!CAUTION]
> Using `time.sleep`, `gevent.sleep`, or other methods for execution delays in LED effects will prevent proper effect termination and cause visual issues on the LED display or other erratic behavior. _See `effect_delay()`_ 


#### LEDEffect(label, handler_fn, valid_events, default_args=None, name=None)

Provides metadata and function linkage for *LED effects*.

Often, `color` will be passed through as an argument, which is an RGB hexadecimal code that can be used to modify the effect's output as appropriate. For example, during the `RACE_LAP_RECORDED` event, color is often determined by the pilot that completed the lap.

- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `handler_fn` (function): function to run when this effect is triggered
- `valid_events` (list): controls whether events can be assigned to various events
- `default_args` _optional_ (dict): provides default arguments for the handler. These arguments will be overwritten if the `Event` provides arguments with the same keys.
- `name` _optional_ (string): internal identifier (auto-generated from `label` if not provided)

By default, an *LED effect* will be available to all *events* that can produce LED output except *LEDEvent.IDLE_DONE*, *LEDEvent.IDLE_RACING*, and *LEDEvent.IDLE_READY*. This can be modified with `valid_events`. It should contain a dict with the following optional keys. Each value should be a list of event identifiers.
- `exclude` (list): this *effect* will never be available for *events* specified here. As a special case, `Evt.ALL` will remove this *effect* from all *events* except those specifically included.
- `include` (list): this *effect* will always be available for *events* specified here  unless specifically excluded.
- `recommended` (list): *effects* in this list will receive priority ordering and visibility in the effect selection UI, at the top of the list, with an asterisk. `Evt.ALL` may be used here.

Normally when an *LED effect*'s handler function completes, the display system will look for a `time` argument and wait this many seconds before switching to an appropriate idle state. You can prevent switching to idle with the `preventIdle` argument, but usually it is more appropriate to set a reasonable `time`.

A list of standard and LED-specific *events* that will accept and trigger *effects* can be found in `src/server/led_event_manager.py`.

Example:
```
LEDEffect(
    "Image: RotorHazard",
    show_bitmap,
    {
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

#### effect_delay(ms, args)

Delay execution of LED effect code, similar to `time.sleep()`. Works asynchronously so main processes continue and provides for clean effect termination when new LED effects are run.

- `ms` (int|float): number of milliseconds to delay
- `args` (dict): args passed to the LEDEffect


### Data Exporters

*Exporters* provide formatting of event data so it may be saved or sent elsewhere. A user may select and run an exporter from the UI, and will be provided with its contents in a file. Plugins may also trigger exports for their own purposes.

*Exporters* must be registered before use. Access to registration is provided though the `register_fn` argument of the `Evt.DATA_EXPORT_INITIALIZE` event. Pass a `DataExporter` object to this method to register it.

For example, an exporter might be registered with the following functions:

```
from eventmanager import Evt
from data_export import DataExporter

def my_formatter_fn(data):
    ...

def my_assembler_fn(rhapi):
    ...

def register_handlers(args):
    args['register_fn'](
        DataExporter(
            "My Exporter",
            my_formatter_function,
            my_assembler_function
        )
    )

def initialize(rhapi):
    rhapi.events.on(Evt.DATA_EXPORT_INITIALIZE, register_handlers)
```

#### DataExporter(label, formatter_fn, assembler_fn, name=None)

Provides metadata and function linkage for *exporters*.

*Exporters* are run in two stages. First, the *assembler* pulls the data needed, then passes it to the *formatter*. In this way, a variety of *assemblers* can share a *formatter*, such as assembling pilot data, heat data, or race data and then passing it to be formatted as CSV or JSON.

- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `formatter_fn` (function): function to run for formatting stage
- `assembler_fn` (function): function to run for assembly stage
- `name` _optional_ (string): internal identifier (auto-generated from `label` if not provided)

The `assembler_fn` receives `rhapi` as an argument so that it may access and prepare timer data as needed.

The `formatter_fn` receives the output of the `assembler_fn`.


### Data Importers

*Importers* accept data and process it so that it can be added to the RH database. A user may select and run an importer from the UI, with a file selector as input. Plugins may also trigger imports for their own purposes.

*Importers* must be registered before use. Access to registration is provided though the `register_fn` argument of the `Evt.DATA_IMPORT_INITIALIZE` event. Pass a `DataImporter` object to this method to register it.

For example, an importer might be registered with the following functions:

```
from eventmanager import Evt
from data_import import DataImporter

def my_import_fn(rhapi, data, args):
    ...

def register_handlers(args):
    args['register_fn'](
        DataImporter(
            "My Importer",
            my_import_fn,
        ),        
    )

def initialize(rhapi):
    rhapi.events.on(Evt.DATA_IMPORT_INITIALIZE, register_handlers)
```

#### DataImporter(label, import_fn, default_args=None, settings=None, name=None)

Provides metadata and function linkage for *importers*.

When an importer is run, the `run_import` method is called, which collates default and locally-provided arguments, then calls the `import_fn`. 

- `label` (string): user-facing text that appears in the RotorHazard frontend interface
- `import_fn` (function): function to run for formatting stage
- `default_args` _optional_ (dict): arguments passed to the `import_fn` when run, unless overridden by local arguments
- `settings` _optional_ (list\[UIField\]): A list of paramters to provide to the user; see [UI Fields](#ui-fields)
- `name` _optional_ (string): internal identifier (auto-generated from `label` if not provided)

The `import_fn` receives as arguments:

- `rhapi` (RHAPI): the RHAPI class
- `data` (any): data to import, provided by the user
- `args` (dict): collated default and locally-provided arguments


### UI Fields

An `RHUI.UIField` object defines a frontend user interface for collecting data. Data is stored in the event by default, or in persistent configuration if the `persistent_section` key is used. If persistent configuration is used, custom sections should be defined using `RHAPI.config.register_section`.

Fields are defined in the following format:

- `name` (string): internal identifier for this parameter; may not begin with `__`
- `label` (string): text that appears in the RotorHazard frontend interface
- `field_type` (UIFieldType), one of:
    - `UIFieldType.TEXT`
    - `UIFieldType.BASIC_INT`
    - `UIFieldType.NUMBER`
    - `UIFieldType.RANGE`
    - `UIFieldType.SELECT`
    - `UIFieldType.CHECKBOX`
    - `UIFieldType.PASSWORD`
    - `UIFieldType.DATE`
    - `UIFieldType.TIME`
    - `UIFieldType.DATETIME`
    - `UIFieldType.EMAIL`
    - `UIFieldType.TEL`
    - `UIFieldType.URL`
- `value` _optional_ (any): Default value for field
- `desc` _optional_ (string): additional user-facing text that appears in the RotorHazard frontend interface describing notes or special instructions for use
- `private` _optional_ (boolean): Prevent automatically generated UI
- `html_attributes` _optional_ (dict): attribute values passed to HTML to control browser-based validation, such as `min`, `max`, `step`, `minlength`, `maxlength`, `pattern`; only valid values for each field type will be added
- `persistent_section`: If defined, this field will save to the server's persistent configuration using the provided input for section; if omitted or `None`, data will save to the event
- `persistent_section`: If set to `True` and `persistent_section` is used, the server will prompt the user to restart the server when this field is altered

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

### Metadata
Plugin authors are strongly encouraged to declare metadata. In your plugin folder, create the JSON-formatted file `manifest.json` using any of the following keys. Currently, keys may be omitted or `null` if not applicable, but some may become required in future versions.

Basic metadata keys include:
- `name`: the name of your plugin
- `author`: the plugin author's name
- `author_uri`: valid HTTP link to the author's website
- `dependencies`: list of [python package requirement specifiers](https://pip.pypa.io/en/stable/reference/requirement-specifiers/)
- `description`: short description of the plugin's function
- `documentation_uri`: valid HTTP link to the plugin's documentation
- `info_uri`: valid HTTP link to a website about the plugin
- `license`: name of the plugin's license
- `license_uri`: valid HTTP link to the plugin's license information
- `required_rhapi_version`: the minimum RHAPI version required to run the plugin, such as "1.1"
- `version`: a version identifier for the plugin's own code ([semver-formatted](https://semver.org/), ideally)
- `zip_filename`: filename of zip package, if separately required for distribution (`null` for GitHub releases)
- `update_uri`: (not yet implemented)
- `text_domain`: (not yet implemented)

#### Community Plugins
Community Plugins can be found, installed, and can be updated entirely through the RotorHazard UI. For a plugin to be included in this section, a manifest is required. Some keys or format of keys are restricted, and additional keys such as `domain` and `category` are also defined. See [Community Plugins documentation](https://rotorhazard.github.io/community-plugins/) for more information. 
