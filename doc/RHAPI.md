# RHAPI

- [Introduction](#introduction)
- [Standard Events](#standard-events)
- [User Interface Helpers](#user-interface-helpers)
- [Data Fields](#data-fields)
- [Database Access](#database-access)
- [Data input/output](#data-input-output)
- [Heat Generation](#heat-generation)
- [Class Ranking](#class-ranking)
- [Race Points](#race-points)
- [LED](#led)
- [Video Receivers](#video-receivers)
- [Active Race](#active-race)
- [Event Results](#event-results)
- [Language and Translation](#language-and-translation)
- [Hardware Interface](#hardware-interface)
- [Sensors Interface](#sensors-interface)


## Introduction

Most plugin interfaces provide access to `RHAPI`, an object providing a wide range of properties and methods across RotorHazard's internal systems. Using RHAPI, one can manipulate nearly every facet of a race event and RotorHazard's behavior.

### API Version

The API version can be read from the `API_VERSION_MAJOR` and `API_VERSION_MINOR` properties.

### Language translation shortcut

The language translation function can be accessed directly via `RHAPI.__()` in addition to its location within `RHAPI.language`.



## Standard Events

Significant timer actions trigger *events*. Plugin authors may bind *handler* functions to events which are run when the event occurs. Many timer subsystems trigger an initialize event so plugins can register behaviors within them. Plugin authors may also bind to and trigger custom events either for their own purposes or to share data between plugins.

A list of timer-provided events is contained within the `Evt` class in `/src/server/eventmanager.py`, which can be accessed with `from eventmanager import Evt`. 

For example, a plugin might register events to be run at startup like this:
```
from eventmanager import Evt

def initialize(rhapi):
    rhapi.events.on(Evt.STARTUP, my_startup_function)
```

### Standard Event Details and Usage

When an *event* is *triggered*, all registered *handlers* are run. *Events* may pass arguments containing useful data such as the node number, pilot callsign, or race object. All events return `args(dict)`, but the available keys will vary.

Register a *handler* using the `.on()` function, usually within your `initialize()` function.

Handlers are given a `name` during registration. One handler with each `name` can be registered per *event*; registering with the same `name` and `event` multiple times will cause handlers to be overridden. Providing a `name` is not needed in most circumstances, as one will be automatically generated if not provided. If multiple *handlers* need bound to the same `event` in one plugin, separate `name`s are required.

*Events* are registered with a *priority* that determines the order handlers are run, lower numbers first. Priorities < 100 are executed synchronously, blocking other code from executing until they finish. Priorities >= 100 are executed asynchronously, allowing the timer to continue running other code. Handlers should generally be run asynchronously, except initial registrations. **Python's `gevents` are not true threads, so code running asynchronously must call `gevent.idle` or `gevent.sleep` at frequent intervals to allow other parts of the server to execute.**

If run asynchronously (priority >= 100), a *handler* will cancel other *handlers* that have the same `name`. For example, only one LED effect can be visible at a time. Handler cancellation can also be prevented by setting a handler's `unique` property to `True`.


#### .on(event, handler_fn, default_args=None, priority=None, unique=False, name=None)
Registers a *handler* to an *event*. This causes the code in the *handler* to be run each time the *event* is *triggered* by any means (timer, plugin, or otherwise). No return.

- `event` (Evt|string): triggering *event* for this *handler*
- `handler_fn` (function): function to run when this event triggers
- `default_args` _optional_ (dict): provides default arguments for the handler; these arguments will be overridden if the `Event` provides arguments with the same keys.
- `priority` _optional_ (int): event priority, as detailed above; if not set, default priority is 75 (synchronous) for intial registrations and 200 (asynchronous) for all others
- `unique` _optional_ (boolean): if set to `True`, this *handler*'s thread will not be cancelled by other *handlers* with the same `name`
- `name` _optional_ (string): sets this handler's `name`; if left unset, the `name` is automatically generated from the module name of the plugin.

#### .off(event, name)

Removes a *handler* from an *event*. Removes only the specific `name` and `event` combination, so if *handlers* with the same `name` are registered to multiple `events`, others will not be removed. No return.

- `event` (string|Evt): the triggering *event* for this *handler*.
- `name` (string): the registered `name` of the handler to remove.

#### .trigger(event, evtArgs=None)

Triggers an *event*, causing all registered *handlers* to run

- `event` (string|Evt): the *event* to trigger
- `evtArgs` (dict): arguments to pass to the handler, overwriting matched keys in that handler's `default_args`



## User Interface Helpers

Interact with RotorHazard's frontend user interface.
These methods are accessed via `RHAPI.ui` 

### UI Panels

Add custom UI panels to RotorHazard's frontend pages. Panels may contain Options and Quickbuttons.

Panels are represented with the `UIPanel` class, which has the following properties:

- `name` (string): Internal identifier for this panel
- `label` (string): Text used as visible panel header
- `page` (string): Page to add panel to
- `order` (int): Not yet implemented
- `open` (boolean): Whether panel is open or closed


#### ui.panels
_Read only_
The list of registered panels. Returns `List[UIPanel]`.

#### ui.register_panel(name, label, page, order=0, open=False)

Register a UI panel and assign it to a page. Returns all panels as `list[UIPanel]`.

- `name` (string): Internal identifier for this panel
- `label` (string): Text used as visible panel header
- `page` (string): Page to add panel to; one of "format", "settings"
- `order` _optional_ (int): Not yet implemented
- `open` _optional_ (boolean): Whether panel is open or closed (default: `False`)

### Quickbuttons

Provides a simple interface to add a UI button and bind it to a function. Quickbuttons appear on assigned UI panels.

Quickbuttons are represented with the `QuickButton` class, which has the following properties:
- `panel` (string): `name` of panel where button will appear
- `name` (string): Internal identifier for this quickbutton
- `label` (string): Text used for visible button label
- `function` (callable): Function to run when button is pressed
- `args` (any): Argument passed to `function` when called

Pass a dict to `args` and parse it in your `function` if multiple arguments are needed.

#### ui.register_quickbutton(panel, name, label, function)
Register a Quickbutton and assign it to a UI panel. Returns all buttons as `list[QuickButton]`.

- `panel` (string): `name` of panel previously registered with `ui.register_panel`
- `name` (string): Internal identifier for this quickbutton
- `label` (string): Text used for visible button label
- `function` (callable): Function to run when button is pressed
- `args` (any): Argument passed to `function` when called

### Markdown

Provides a simple interface to add a UI Markdown block to a panel.

Markdown blocks are represented with the `Markdown` class, which has the following properties:

- `panel` (string): `name` of panel where markdown will appear
- `name` (string): Internal identifier for this markdown block
- `desc` (string): Markdown-formatted text to display

#### ui.register_markdown(panel, name, desc)

Register a Markdown block and assign it to a UI panel.

- `panel` (string): `name` of panel previously registered with `ui.register_panel`
- `name` (string): Internal identifier for this markdown block
- `desc` (string): Markdown-formatted text to display

### Pages

Add custom pages to RotorHazard's frontend with [Flask Blueprints](https://flask.palletsprojects.com/blueprints/). 

#### ui.blueprint_add(blueprint)
Adds a Flask Blueprint which can be used to provide access to custom pages/URLs.

- `blueprint` (blueprint): Flask Blueprint object

### UI Messages

Send messages to RotorHazard's frontend.

#### ui.message_speak(message)
Send a message which is parsed by the text-to-speech synthesizer.

- `message` (string): Text of message to be spoken

#### ui.message_notify(message)
Send a message which appears in the message center and notification bar.

- `message` (string): Text of message to display

#### ui.message_alert(message)
Send a message which appears as a pop-up alert.

- `message` (string): Text of message to display

### Sockets

#### ui.socket_listen(message, handler)
Calls function when a socket event is received.
- `message` (string): Socket event name
- `handler` (callable): Function to call

`handler` is passed socket data as an argument.

### Data Broadcast

Update data displayed on frontend. Use after modifying data structures with other API methods.

#### ui.broadcast_ui(page):
Broadcast UI panel setup to all connected clients.

- `page` (string): Page to update

#### ui.broadcast_frequencies():
Broadcast seat frequencies to all connected clients.

#### ui.broadcast_pilots():
Broadcast pilot data to all connected clients.

#### ui.broadcast_heats():
Broadcast heat data to all connected clients.

#### ui.broadcast_raceclasses():
Broadcast race class data to all connected clients.

#### ui.broadcast_raceformats():
Broadcast race format data to all connected clients.

#### ui.broadcast_current_heat():
Broadcast current heat selection to all connected clients.

#### ui.broadcast_frequencyset():
Broadcast frequency set data to all connected clients.

#### ui.broadcast_race_status():
Broadcast race setup and status to all connected clients.



## Data Fields

Create and access new data structures.
These methods are accessed via `RHAPI.fields` 


### Options
Options are simple storage variables which persist to the database and can be presented to users through frontend UI. Each option takes a single value.

#### fields.options
_Read only_
Provide a list of options registered by plugins. Does not include built-in options or fields registered as persistent configuration.

#### fields.register_option(field, panel=None, order=0)
Register an option and optionally assign it to be displayed on a UI panel.

- `field` (UIField): See [UI Fields](Plugins.md#ui-fields)
- `panel` _optional_ (string): `name` of panel previously registered with `ui.register_panel`
- `order` _optional_ (int): Not yet implemented


### Pilot Attributes

Pilot Attributes are simple storage variables which persist to the database and can be presented to users through frontend UI. Pilot Attribute values are unique to/stored individually for each pilot.

Pilot Attributes are represented with the `PilotAttribute` class, which has the following properties:
- `id` (int): ID of pilot to which this attribute is assigned
- `name` (string): Name of attribute
- `value` (string): Value of attribute

Alter pilot attributes with `db.pilot_alter`.

#### fields.pilot_attributes
_Read only_
Provides a list of registered `PilotAttribute`s.

#### fields.register_pilot_attribute(field)
Register an attribute to be displayed in the UI or otherwise made accessible to plugins.

- `field` (UIField): See [UI Fields](Plugins.md#ui-fields)


### Heat Attributes

Heat Attributes are simple storage variables which persist to the database. Heat Attribute values are unique to/stored individually for each heat.

Heat Attributes are represented with the `HeatAttribute` class, which has the following properties:
- `id` (int): ID of heat to which this attribute is assigned
- `name` (string): Name of attribute
- `value` (string): Value of attribute

Alter heat attributes with `db.heat_alter`.

#### fields.heat_attributes
_Read only_
Provides a list of registered `HeatAttribute`s.

#### fields.register_heat_attribute(field)
Register an attribute to be made accessible to plugins.

- `field` (UIField): See [UI Fields](Plugins.md#ui-fields)


### Race Class Attributes

Race Class Attributes are simple storage variables which persist to the database. Race Class Attribute values are unique to/stored individually for each race class.

Heat Attributes are represented with the `RaceClassAttribute` class, which has the following properties:
- `id` (int): ID of race class to which this attribute is assigned
- `name` (string): Name of attribute
- `value` (string): Value of attribute

Alter race class attributes with `db.raceclass_alter`.

#### fields.raceclass_attributes
_Read only_
Provides a list of registered `RaceClassAttribute`s.

#### fields.register_raceclass_attribute(field)
Register an attribute to be made accessible to plugins.

- `field` (UIField): See [UI Fields](Plugins.md#ui-fields)


### Race Attributes

Race Attributes are simple storage variables which persist to the database. Race Attribute values are unique to/stored individually for each race.

Race Attributes are represented with the `SavedRaceMetaAttribute` class, which has the following properties:
- `id` (int): ID of race to which this attribute is assigned
- `name` (string): Name of attribute
- `value` (string): Value of attribute

Alter race attributes with `db.race_alter`.

#### fields.race_attributes
_Read only_
Provides a list of registered `SavedRaceMetaAttribute`s.

#### fields.register_race_attribute(field)
Register an attribute to be made accessible to plugins.

- `field` (UIField): See [UI Fields](Plugins.md#ui-fields)


### Race Format Attributes

Race Format Attributes are simple storage variables which persist to the database. Race Format Attribute values are unique to/stored individually for each race format.

Race Format Attributes are represented with the `RaceFormatAttribute` class, which has the following properties:
- `id` (int): ID of race format to which this attribute is assigned
- `name` (string): Name of attribute
- `value` (string): Value of attribute

Alter race attributes with `db.raceformat_alter`.

#### fields.raceformat_attributes
_Read only_
Provides a list of registered `SavedRaceMetaAttribute`s.

#### fields.register_raceformat_attribute(field)
Register an attribute to be made accessible to plugins.

- `field` (UIField): See [UI Fields](Plugins.md#ui-fields)


## Database Access

Read and modify database values.
These methods are accessed via `RHAPI.db` 

### Global
Properties and methods spanning the entire stored event.

#### db.event_results
_Read only_
Returns cumulative totals for all saved races as `dict`.

#### db.reset_all()
Resets database to default state.

### Pilots
A pilot is an individual participant. In order to participate in races, pilots can be assigned to multiple heats.

Pilots are represented with the `Pilot` class, which has the following properties:
- `id` (int): Internal identifier 
- `callsign` (string): Callsign
- `team` (string): Team designation
- `phonetic` (string): Phonetically-spelled callsign, used for text-to-speech
- `name` (string): Real name
- `color` (string): Hex-encoded color
- `used_frequencies` (string): Serialized list of frequencies this pilot has been assigned when starting a race, ordered by recency
- `active` (boolean): Not yet implemented

The sentinel value `RHUtils.PILOT_ID_NONE` should be used when no pilot is defined.


#### db.pilots
_Read only_
All pilot records. Returns `list[Pilot]`.

#### db.pilot_by_id(pilot_id)
A single pilot record. Does not include custom attributes. Returns `Pilot`.
- `pilot_id` (int): ID of pilot record to retrieve

#### db.pilot_attributes(pilot_or_id)
All custom attributes assigned to pilot. Returns `list[PilotAttribute]`.
- `pilot_or_id` (pilot|int): Either the pilot object or the ID of pilot

#### db.pilot_attribute_value(pilot_or_id, name, default_value=None)
The value of a single custom attribute assigned to pilot. Returns `string` regardless of registered field type, or default value.
- `pilot_or_id` (pilot|int): Either the pilot object or the ID of pilot
- `name` (string): attribute to retrieve
- `default_value` _(optional)_: value to return if attribute is not registered (uses registered default if available)

#### db.pilot_ids_by_attribute(name, value)
ID of pilots with attribute matching the specified attribute/value combination. Returns `list[int]`.
- `name` (string): attribute to match
- `value` (string): value to match

#### db.pilot_add(name=None, callsign=None, phonetic=None, team=None, color=None)
Add a new pilot to the database. Returns the new `Pilot`.
- `name` _(optional)_ (string): Name for new pilot
- `callsign` _(optional)_ (string): Callsign for new pilot
- `phonetic` _(optional)_ (string): Phonetic spelling for new pilot callsign
- `team` _(optional)_ (string): Team for new pilot
- `color` _(optional)_ (string): Color for new pilot

#### db.pilot_alter(pilot_id, name=None, callsign=None, phonetic=None, team=None, 
Alter pilot data. Returns the altered `Pilot`
- `pilot_id` (int): ID of pilot to alter
- `name` _(optional)_ (string): New name for pilot
- `callsign` _(optional)_ (string): New callsign for pilot
- `phonetic` _(optional)_ (string): New phonetic spelling of callsign for pilot
- `team` _(optional)_ (string): New team for pilot
- `color` _(optional)_ (string): New color for pilot
- `attributes` _(optional)_ (dict): Attributes to alter, attribute values assigned to respective keys

#### db.pilot_delete(pilot_or_id)
Delete pilot record. Fails if pilot is associated with saved race. Returns `boolean` success status.
- `pilot_or_id` (int): ID of pilot to delete 

#### db.pilots_reset()
Delete all pilot records. No return value.


### Heats
Heats are collections of pilots upon which races are run. A heat may first be represented by a heat plan which defines methods for assigning pilots. The plan must be seeded into pilot assignments in order for a race to be run.

Heats are represented with the `Heat` class, which has the following properties:
- `id` (int): Internal identifier
- `name` (string): User-facing name
- `class_id` (int): ID of associated race class
- `results` (dict|None): Internal use only; see below
- `_cache_status`: Internal use only
- `order` (int): Not yet implemented
- `status` (HeatStatus): Current status of heat as `PLANNED` or `CONFIRMED`
- `auto_frequency` (boolean): True to assign pilot seats automatically, False for direct assignment
- `active` (boolean): Not yet implemented

The sentinel value `RHUtils.HEAT_ID_NONE` should be used when no heat is defined.

NOTE: Results should be accessed with the `db.heat_results` method and not by reading the `results` property directly. The `results` property is unreliable because results calulation is delayed to improve system performance. `db.heat_results` ensures the calculation is current, will return quickly from cache if possible, or will build it if necessary.

#### db.heats
_Read only_
All heat records. Returns `list[Heat]`

#### db.heat_by_id(heat_id)
A single heat record. Returns `Heat`.
- `heat_id` (int): ID of heat record to retrieve

#### db.heats_by_class(raceclass_id)
All heat records associated with a specific class. Returns `list[Heat]`
- `raceclass_id` (int): ID of raceclass used to retrieve heats

#### db.heat_results(heat_or_id)
The calculated summary result set for all races associated with this heat. Returns `dict`.
- `heat_or_id` (int|Heat): Either the heat object or the ID of heat

#### db.heat_max_round(heat_id)
The highest-numbered race round recorded for selected heat. Returns `int`.
- `heat_id` (int): ID of heat

#### db.heat_attributes(heat_or_id)
All custom attributes assigned to heat. Returns `list[HeatAttribute]`.
- `heat_or_id` (heat|int): Either the heat object or the ID of heat

#### db.heat_attribute_value(heat_or_id, name, default_value=None)
The value of a single custom attribute assigned to heat. Returns `string` regardless of registered field type, or default value.
- `heat_or_id` (heat|int): Either the heat object or the ID of heat
- `name` (string): attribute to retrieve
- `default_value` _(optional)_: value to return if attribute is not registered (uses registered default if available)

#### db.heat_ids_by_attribute(name, value)
ID of heats with attribute matching the specified attribute/value combination. Returns `list[int]`.
- `name` (string): attribute to match
- `value` (string): value to match

#### db.heat_add(name=None, raceclass=None, auto_frequency=None)
Add a new heat to the database. Returns the new `Heat`.
- `name` _(optional)_ (string): Name for new heat
- `raceclass` _(optional)_ (int): Raceclass ID for new heat
- `auto_frequency` _(optional)_ (boolean): Whether to enable auto-frequency

#### db.heat_duplicate(source_heat_or_id, dest_class=None)
Duplicate a heat record. Returns the new `Heat`.
- `source_heat_or_id` (int|heat): Either the heat object or the ID of heat to copy from
- `dest_class` _(optional)_ (int): Raceclass ID to copy heat into

#### db.heat_alter(heat_id, name=None, raceclass=None, auto_frequency=None, status=None, attributes=None)
Alter heat data. Returns tuple of this `Heat` and affected races as `list[SavedRace]`.
- `heat_id` (int): ID of heat to alter
- `name` _(optional)_ (string): New name for heat
- `raceclass` _(optional)_ (int): New raceclass ID for heat
- `auto_frequency` _(optional)_ (boolean): New auto-frequency setting for heat
- `status` _(optional)_ (HeatStatus): New status for heat
- `attributes` _(optional)_ (dict): Attributes to alter, attribute values assigned to respective keys

#### db.heat_delete(heat_or_id)
Delete heat. Fails if heat has saved races associated or if there is only one heat left in the database. Returns `boolean` success status.
- `heat_or_id` (int|heat): ID of heat to delete

#### db.heats_reset()
Delete all heat records. No return value.


### Heat &rarr; Slots
Slots are data structures containing a pilot assignment or assignment method. Heats contain one or more Slots corresponding to pilots who may participate in the Heat. When a heat is calculated, the `method` is used to reserve a slot for a given pilot. Afterward, `pilot` contains the ID for which the space is reserved. A Slot assignment is only a reservation, it does not mean the pilot has raced regardless of heat `status`.

Slots are represented with the `HeatNode` class, which has the following properties:
- `id` (int): Internal identifier
- `heat_id` (int): ID of heat to which this slot is assigned
- `node_index` (int): slot number
- `pilot_id` (int|None): ID of pilot assigned to this slot
- `color` (string): hexadecimal color assigned to this slot
- `method` (ProgramMethod): Method used to implement heat plan
- `seed_rank` (int): Rank value used when implementing heat plan
- `seed_id` (int): ID of heat or class used when implementing heat plan

`Database.ProgramMethod` defines the method used when a heat plan is converted to assignments:
- `ProgramMethod.NONE`: No assignment made
- `ProgramMethod.ASSIGN`: Use pilot already defined in `pilot_id`
- `ProgramMethod.HEAT_RESULT`: Assign using `seed_id` as a heat designation
- `ProgramMethod.CLASS_RESULT`: Assign using `seed_id` as a race class designation

Import `ProgramMethod` with:
`from Database import ProgramMethod`

#### db.slots
_Read only_
All slot records. Returns `list[HeatNode]`.

#### db.slots_by_heat(heat_id)
Slot records associated with a specific heat. Returns `list[HeatNode]`.
- `heat_id` (int): ID of heat used to retrieve slots

#### db.slot_alter(slot_id, method=None, pilot=None, seed_heat_id=None, seed_raceclass_id=None, seed_rank=None)
Alter slot data. Returns tuple of associated `Heat` and affected races as `list[SavedRace]`.
- `slot_id` (int): ID of slot to alter
- `method` _(optional)_ (ProgramMethod): New seeding method for slot
- `pilot` _(optional)_ (int): New ID of pilot assigned to slot
- `seed_heat_id` _(optional)_ (): New heat ID to use for seeding
- `seed_raceclass_id` _(optional)_ (int): New raceclass ID to use for seeding
- `seed_rank` _(optional)_ (int): New rank value to use for seeding

With `method` set to `ProgramMethod.NONE`, most other fields are ignored. Only use `seed_heat_id` with `ProgramMethod.HEAT_RESULT`, and `seed_raceclass_id` with `ProgramMethod.CLASS_RESULT`, otherwise the assignment is ignored.

#### db.slots_alter_fast(slot_list)
Make many alterations to slots in a single database transaction as quickly as possible. Use with caution. May accept invalid input. Does not trigger events, clear associated results, or update cached data. These operations must be done manually if required. No return value.
- `slot_list`: a `list` of `dicts` in the following format:
	- `slot_id` (int): ID of slot to alter
	- `method` _(optional)_ (ProgramMethod): New seeding method for slot
	- `pilot` _(optional)_ (int): New ID of pilot assigned to slot
	- `seed_heat_id` _(optional)_ (): New heat ID to use for seeding
	- `seed_raceclass_id` _(optional)_ (int): New raceclass ID to use for seeding
	- `seed_rank` _(optional)_ (int): New rank value to use for seeding



### Race Classes
Race classes are groups of related heats. Classes may be used by the race organizer in many different ways, such as splitting sport and pro pilots, practice/qualifying/mains, primary/consolation bracket, etc.

Race classes are represented with the `RaceClass` class, which has the following properties:
- `id` (int): Internal identifier
- `name` (string): User-facing name
- `description` (string): User-facing long description, accepts markdown
- `format_id` (int): ID for class-wide required race format definition
- `win_condition` (string): ranking algorithm
- `results` (dict|None): Internal use only; see below
- `_cache_status`: Internal use only
- `ranking` (dict|None): Calculated race class ranking
- `rank_settings` (string): JSON-serialized arguments for ranking algorithm
- `_rank_status`: Internal use only
- `rounds` (int): Number of expected/planned rounds each heat will be run
- `heat_advance_type` (HeatAdvanceType): Method used for automatic heat advance
- `round_type` (RoundType): Method used for determining round groupings
- `order` (int): Not yet implemented
- `active` (boolean): Not yet implemented

The sentinel value `RHUtils.CLASS_ID_NONE` should be used when no race class is defined.

NOTE: Results should be accessed with the `db.raceclass_results` method and not by reading the `results` property directly. The `results` property is unreliable because results calculation is delayed to improve system performance. `db.raceclass_results` ensures the calculation is current, will return quickly from cache if possible, or will build it if necessary.

`Database.HeatAdvanceType` defines how the UI will automatically advance heats after a race is finished.
- `HeatAdvanceType.NONE`: Do nothing
- `HeatAdvanceType.NEXT_HEAT`: Advance heat; if all `rounds` run advance race class
- `HeatAdvanceType.NEXT_ROUND`: Advance heat if `rounds` has been reached; advance race class after last heat in class

#### db.raceclasses
_Read only_
All race class records. Returns `list[RaceClass]`.

#### db.raceclass_by_id(raceclass_id)
A single race class record. Returns `RaceClass`.
- `raceclass_id` (int): ID of race class record to retrieve

#### db.raceclass_attributes(raceclass_or_id)
All custom attributes assigned to race class. Returns `list[RaceClassAttribute]`.
- `raceclass_or_id` (raceclass|int): Either the race class object or the ID of race class

#### db.raceclass_attribute_value(raceclass_or_id, name, default_value=None)
The value of a single custom attribute assigned to race class. Returns `string` regardless of registered field type, or default value.
- `raceclass_or_id` (raceclass|int): Either the race class object or the ID of race class
- `name` (string): attribute to retrieve
- `default_value` _(optional)_: value to return if attribute is not registered (uses registered default if available)

#### db.raceclass_ids_by_attribute(name, value)
ID of race classes with attribute matching the specified attribute/value combination. Returns `list[int]`.
- `name` (string): attribute to match
- `value` (string): value to match

#### db.raceclass_add(name=None, description=None, raceformat=None, win_condition=None, rounds=None, heat_advance_type=None, round_type=None)
Add a new race class to the database. Returns the new `RaceClass`.
- `name` _(optional)_ (string): Name for new race class
- `description` _(optional)_ (string): Description for new race class
- `raceformat` _(optional)_ (int): ID of format to assign
- `win_condition` _(optional)_ (string): Class ranking identifier to assign
- `rounds` _(optional)_ (int): Number of rounds to assign to race class
- `heat_advance_type` _(optional)_ (HeatAdvanceType): Advancement method to assign to race class
- `round_type` _(optional)_ (RoundType): Method used for determining round groupings
- 
#### db.raceclass_duplicate(source_class_or_id)
Duplicate a race class. Returns the new `RaceClass`.
- `source_class_or_id` (int|RaceClass): Either a race class object or the ID of a race class

#### db.raceclass_alter(raceclass_id, name=None, description=None, raceformat=None, win_condition=None, rounds=None, heat_advance_type=None, round_type=None, rank_settings=None, attributes=None)
Alter race class data. Returns tuple of this `RaceClass` and affected races as `list[SavedRace]`.
- `raceclass_id` (int): ID of race class to alter
- `name` _(optional)_ (string): Name for new race class
- `description` _(optional)_ (string): Description for new race class
- `raceformat` _(optional)_ (int): ID of format to assign
- `win_condition` _(optional)_ (string): Class ranking identifier to assign
- `rounds` _(optional)_ (int): Number of rounds to assign to race class
- `heat_advance_type` _(optional)_ (HeatAdvanceType): Advancement method to assign to race class
- `round_type` _(optional)_ (RoundType): Method used for determining round groupings- 
- `rank_settings` _(optional)_ (dict): arguments to pass to class ranking
- `attributes` _(optional)_ (dict): Attributes to alter, attribute values assigned to respective keys

#### db.raceclass_results(raceclass_or_id)
The calculated summary result set for all races associated with this race class. Returns `dict`.
- `raceclass_or_id` (int|RaceClass): Either the race class object or the ID of race class

#### db.raceclass_ranking(raceclass_or_id)
The calculated ranking associated with this race class. Returns `dict`.
- `raceclass_or_id` (int|RaceClass): Either the race class object or the ID of race class

#### db.raceclass_delete(raceclass_or_id)
Delete race class. Fails if race class has saved races associated. Returns `boolean` success status.
- `raceclass_or_id` (int|RaceClass): Either the race class object or the ID of race class

#### db.raceclasses_reset()
Delete all race classes. No return value.


### Race Formats
Race formats are profiles of properties used to define parameters of individual races. Every race has an assigned format. A race formats may be assigned to a race class, which forces RotorHazard to switch to that formatwhen running races within the class.

Race formats are represented with the `RaceFormat` class, which has the following properties:
- `id` (int): Internal identifier
- `name` (string): User-facing name
- `unlimited_time` (int): True(1) if race clock counts up, False(0) if race clock counts down
- `race_time_sec` (int): Race clock duration in seconds, unused if `unlimited_time` is True(1)
- `lap_grace_sec` (int): Grace period duration in seconds, -1 for unlimited, unused if `unlimited_time` is True(1)
- `staging_fixed_tones` (int): Number of staging tones always played regardless of random delay
- `start_delay_min_ms` (int): Minimum period for random phase of staging delay in milliseconds
- `start_delay_max_ms` (int): Maximum duration of random phase of staging delay in milliseconds
- `staging_delay_tones` (int): Whether to play staging tones each second during random delay phase
- `number_laps_win` (int): Number of laps used to declare race winner, if > 0
- `win_condition` (int): Condition used to determine race winner and race ranking
- `team_racing_mode` (int): Racing mode, 0 for individual, 1 for team, 2 for co-op
- `start_behavior` (int): Handling of first crossing
- `points_method` (String): JSON-serialized arguments for points algorithm

The sentinel value `RHUtils.FORMAT_ID_NONE` should be used when no race format is defined.

The following values are valid for `staging_delay_tones`.
- 0: None
- 2: Each Second

The following values are valid for `win_condition`.
- 0: None
- 1: Most Laps in Fastest Time
- 2: First to X Laps
- 3: Fastest Lap
- 4: Fastest Consecutive Laps
- 5: Most Laps Only
- 6: Most Laps Only with Overtime

The following values are valid for `start_behavior`.
- 0: Hole Shot
- 1: First Lap
- 2: Staggered Start

**Notice:** The race format specification is expected to be modified in future versions. Please consider this while developing plugins.
- The type for `staging_delay_tones` may change to boolean.
- The type for `unlimited_time` may change to boolean.
- The type for `win_condition` may change to a members of dedicated class or become string-based for extensibility.
- The type for `start_behavior` may change to a members of dedicated class.

#### db.raceformats
_Read only_
All race formats. Returns `list[RaceFormat]`

#### db.raceformat_by_id(format_id)
A single race format record. Returns `RaceFormat`.
- `format_id` (int): ID of race format record to retrieve

#### db.raceformat_attributes(raceformat_or_id)
All custom attributes assigned to race format. Returns `list[RaceFormatAttribute]`.
- `raceformat_or_id` (raceformat|int): Either the race format object or the ID of race format

#### db.raceformat_attribute_value(raceformat_or_id, name, default_value=None)
The value of a single custom attribute assigned to race format. Returns `string` regardless of registered field type, or default value.
- `raceformat_or_id` (raceformat|int): Either the race format object or the ID of race format
- `name` (string): attribute to retrieve
- `default_value` _(optional)_: value to return if attribute is not registered (uses registered default if available)

#### db.raceformat_ids_by_attribute(name, value)
ID of race formats with attribute matching the specified attribute/value combination. Returns `list[int]`.
- `name` (string): attribute to match
- `value` (string): value to match

#### db.raceformat_add(name=None, unlimited_time=None, race_time_sec=None, lap_grace_sec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None)
Add a new race format to the database. Returns the new `RaceFormat`.
- `name` _(optional)_ (string): Name for new race format
- `unlimited_time` _(optional)_ (int): Unlimited Time setting for new race format
- `race_time_sec` _(optional)_ (int): Race duration for new race format
- `lap_grace_sec` _(optional)_ (int): Grace period for new race format
- `staging_fixed_tones` _(optional)_ (int): Fixed tones for new race format
- `staging_delay_tones` _(optional)_ (int): Delay tones setting for new race format
- `start_delay_min_ms` _(optional)_ (int): Delay minimum for new race format
- `start_delay_max_ms` _(optional)_ (int): Maximum delay duration for new race format
- `start_behavior` _(optional)_ (int): First crossing behavior for new race format
- `win_condition` _(optional)_ (int): Win condition for new race format
- `number_laps_win` _(optional)_ (int): Lap count setting for new race format
- `team_racing_mode` _(optional)_ (int): Racing mode, 0 for individual, 1 for team, 2 for co-op
- `points_method` _(optional)_ (string): JSON-serialized arguments for new race format

#### db.raceformat_duplicate(source_format_or_id)
Duplicate a race format. Returns the new `RaceFormat`.
- `source_format_or_id` (int|RaceFormat): Either a race format object or the ID of a race format

#### db.raceformat_alter(raceformat_id, name=None, unlimited_time=None, race_time_sec=None, lap_grace_sec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None, points_settings=None, attributes=None)
Alter race format data. Returns tuple of this `RaceFormat` and affected races as `list[SavedRace]`.
- `raceformat_id` (int): ID of race format to alter
- `name` _(optional)_ (string): Name for new race format
- `unlimited_time` _(optional)_ (int): Unlimited Time setting for new race format
- `race_time_sec` _(optional)_ (int): Race duration for new race format
- `lap_grace_sec` _(optional)_ (int): Grace period for new race format
- `staging_fixed_tones` _(optional)_ (int): Fixed tones for new race format
- `staging_delay_tones` _(optional)_ (int): Delay tones setting for new race format
- `start_delay_min_ms` _(optional)_ (int): Delay minimum for new race format
- `start_delay_max_ms` _(optional)_ (int): Maximum delay duration for new race format
- `start_behavior` _(optional)_ (int): First crossing behavior for new race format
- `win_condition` _(optional)_ (int): Win condition for new race format
- `number_laps_win` _(optional)_ (int): Lap count setting for new race format
- `team_racing_mode` _(optional)_ (int): Racing mode, 0 for individual, 1 for team, 2 for co-op
- `points_method` _(optional)_ (string): JSON-serialized arguments for new race format
- `points_settings`  _(optional)_ (dict): arguments to pass to class ranking
- `attributes` _(optional)_ (dict): Attributes to alter, attribute values assigned to respective keys

#### db.raceformat_delete(raceformat_id)
Delete race format. Fails if race class has saved races associated, is assigned to the active race, or is the last format in database. Returns `boolean` success status.
- `raceformat_id` (int): ID of race format to delete

#### db.raceformats_reset()
Resets race formats to default. No return value.


### Frequency Sets
Frequency sets contain a mapping of band/channel/frequency values to seats. They also store enter and exit values.

Frequency sets are represented with the `Profiles` class, which has the following properties:
- `id` (int): Internal identifier
- `name` (string): User-facing name
- `description` (string): User-facing long description
- `frequencies` (string): JSON-serialized frequency objects per seat
- `enter_ats` (string): JSON-serialized enter-at points per seat
- `exit_ats` (string): JSON-serialized exit-at points per seat 
- `f_ratio` (int): Unused legacy value

`frequencies` can be JSON-unserialized (json.loads) to a dict:
- `b`: list of band designations, ordered by seat number; values may string be null
- `c`: list of band-channel designations, ordered by seat number; values may int be null
- `f`: list of frequencies, ordered by seat number; values are int

`enter_ats` and `exit_ats` can be JSON-unserialized (json.loads) to a dict:
- `v`: list of enter/exit values, ordered by seat number; values are int

The length of lists stored in `frequencies`, `enter_ats`, and `exit_ats` may not match the number of seats. In these cases values are either not yet available (if too few) or no longer used (if too many) for higher-index seats.

The sentinel value `RHUtils.FREQUENCY_ID_NONE` should be used when no frequency is defined.

**Notice:** The frequency set specification is expected to be modified in future versions. Please consider this while developing plugins.
- Rename class
- Siimplify serialization for `enter_ats`, `exit_ats`
- Remove of unused `f_ratio`

#### db.frequencysets
_Read only_
All frequency set records. Returns `list[Profiles]`.

#### db.frequencyset_by_id(set_id)
A single frequency set record. Returns `Profiles`.
- `set_id` (int): ID of frequency set record to retrieve

#### db.frequencyset_add(name=None, description=None, frequencies=None, enter_ats=None, exit_ats=None)
Add a new frequency set to the database. Returns the new `Profiles`.
- `name` (string): Name for new frequency set
- `description` (string): Description for new frequency set
- `frequencies` (string|dict): Frequency, band, and channel information for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form
- `enter_ats` (string|dict): Enter-at points for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form
- `exit_ats` (string|dict): Exit-at points for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form

#### db.frequencyset_duplicate(source_set_or_id)
Duplicate a frequency set. Returns the new `Profiles`.
- `source_set_or_id` (int|Profiles): Either a frequency set object or the ID of a frequency set

#### db.frequencyset_alter(set_id, name=None, description=None, frequencies=None, enter_ats=None, exit_ats=None)
Alter frequency set data. Returns the altered `Profiles` object.
- `set_id` (int): ID of frequency set to alter
- `name` (string): Name for new frequency set
- `description` (string): Description for new frequency set
- `frequencies` (string|dict): Frequency, band, and channel information for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form
- `enter_ats` (string|dict): Enter-at points for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form
- `exit_ats` (string|dict): Exit-at points for new frequency set, as described above in serialized JSON (string) or unserialized (dict) form

#### db.frequencyset_delete(set_or_id)
Delete frequency set. Fails if frequency set is last remaining. Returns `boolean` success status.
- `set_or_id` (int|Profiles): Either a frequency set object or the ID of a frequency set

#### db.frequencysets_reset()
Resets frequency sets to default. No return value.

### Saved Races
Saved races are sets of stored information about race history. The Saved race object stores results and metadata. For a complete picture of a saved race, it is necessary to fetch associated _Pilot Runs_ and _Laps_.

Saved races are represented with the `SavedRaceMeta` class, which has the following properties:
- `id` (int): Internal identifier
- `round_id` (int): round number
- `heat_id` (int): ID of associated heat
- `class_id` (int): ID of associated race class, or `CLASS_ID_NONE`
- `format_id` (int): ID of associated race format
- `start_time` (int): Internal (monotonic) time value of race start
- `start_time_formatted` (string): Human-readable time of race start
- `results` (dict|None): Internal use only; see below
- `_cache_status`: Internal use only

NOTE: Results should be accessed with the `db.race_results` method and not by reading the `results` property directly. The `results` property is unreliable because results calulation is delayed to improve system performance. `db.race_results` ensures the calculation is current, will return quickly from cache if possible, or will build it if necessary.

#### db.races
_Read only_
All saved race records. Returns `list[SavedRaceMeta]`.

#### db.race_by_id(race_id)
A single saved race record, retrieved by ID. Returns `SavedRaceMeta`.
- `race_id` (int): ID of saved race record to retrieve

#### db.race_by_heat_round(heat_id, round_number)
A single saved race record, retrieved by heat and round. Returns `SavedRaceMeta`.
- `heat_id` (int): ID of heat used to retrieve saved race
- `round_number` (int): round number used to retrieve saved race

#### db.races_by_heat(heat_id)
Saved race records matching the provided heat ID. Returns `list[RaceClass]`.
- `heat_id` (int): ID of heat used to retrieve saved race

#### db.races_by_raceclass(raceclass_id)
Saved race records matching the provided race class ID. Returns `list[RaceClass]`.
- `raceclass_id` (int): ID of race class used to retrieve saved race

#### db.race_attributes(race_or_id)
All custom attributes assigned to race. Returns `list[SavedRaceMetaAttribute]`.
- `race_or_id` (race|int): Either the race object or the ID of race

#### db.race_attribute_value(race_or_id, name, default_value=None)
The value of a single custom attribute assigned to race. Returns `string` regardless of registered field type, or default value.
- `race_or_id` (race|int): Either the race object or the ID of race
- `name` (string): attribute to retrieve
- `default_value` _(optional)_: value to return if attribute is not registered (uses registered default if available)

#### db.race_ids_by_attribute(name, value)
ID of races with attribute matching the specified attribute/value combination. Returns `list[int]`.
- `name` (string): attribute to match
- `value` (string): value to match

#### db.race_add(round_id, heat_id, class_id, format_id, start_time, start_time_formatted)
Add a saved race directly in the database. Returns `SavedRaceMeta`.
- `round_id` (int): round number
- `heat_id` (int): ID of associated heat
- `class_id` (int): ID of associated race class, or `CLASS_ID_NONE`
- `format_id` (int): ID of associated race format
- `start_time` (int): Internal (monotonic) time value of race start
- `start_time_formatted` (string): Human-readable time of race start

#### db.race_alter(race_id, attributes=None)
Alter race data. Supports only custom attributes. No return value.
- `race_id` (int): ID of race to alter
- `attributes` _(optional)_ (list[dict]): Attributes to alter, attribute values assigned to respective keys

#### db.race_results(race_or_id)
Calculated result set for saved race. Returns `dict`.
- `race_or_id` (int|SavedRaceMeta): Either the saved race object or the ID of saved race

#### db.races_clear()
Delete all saved races. No return value.


### Saved Race &rarr; Pilot Runs
Pilot Runs store data related to individual pilots in each race, except lap crossings. Each saved race has one or more pilot runs associated with it.

Saved races are represented with the `SavedPilotRace` class, which has the following properties:
- `id` (int): Internal identifier
- `race_id` (int): ID of associated saved race
- `node_index` (int): Seat number
- `pilot_id` (int): ID of associated pilot
- `history_values` (string): JSON-serialized raw RSSI data
- `history_times` (string): JSON-serialized timestamps for raw RSSI data 
- `penalty_time` (int): Not implemented
- `penalty_desc` (string): Not implemented
- `enter_at` (int): Gate enter calibration point
- `exit_at` (int): Gate exit calibration point
- `frequency` (int): Active frequency for this seat at race time

#### db.pilotruns
_Read only_
All pilot run records. Returns `list[SavedPilotRace]`.

#### db.pilotrun_by_id(run_id)
A single pilot run record, retrieved by ID. Returns `SavedPilotRace`.
- `run_id` (int): ID of pilot run record to retrieve

#### db.pilotruns_by_race(race_id)
Pilot run records matching the provided saved race ID. Returns `list[SavedPilotRace]`.
- `race_id` (int): ID of saved race used to retrieve pilot runs

#### db.pilotrun_add(race_id, node_index, pilot_id, history_values, history_times, enter_at, exit_at, frequency, laps)
Add a `SavedPilotRace` directly in the database. Laps must be added during creation. Returns `SavedPilotRace`.
- `race_id` (int): ID of associated saved race
- `node_index` (int): Seat number
- `pilot_id` (int): ID of associated pilot
- `history_values` (string): JSON-serialized raw RSSI data
- `history_times` (string): JSON-serialized timestamps for raw RSSI data 
- `enter_at` (int): Gate enter calibration point
- `exit_at` (int): Gate exit calibration point
- `frequency` (int): Active frequency for this seat at race time
- `laps` (list[Crossing]): List of `Crossing` objects to add to this run

### Saved Race &rarr; Pilot Run &rarr; Laps
Laps store data related to start gate crossings. Each pilot run may have one or more laps associated with it. When displaying laps, be sure to reference the associated race format.

Laps are represented with the `SavedRaceLap` class, which has the following properties:
- `id` (int): Internal identifier
- `race_id` (int): ID of associated saved race
- `pilotrace_id` (int): ID of associated pilot run
- `node_index` (int): Seat number
- `pilot_id` (int): ID of associated pilot
- `lap_time_stamp` (int): Milliseconds since race start time
- `lap_time` (int): Milliseconds since previous counted lap
- `lap_time_formatted` (string): Formatted user-facing text
- `source` (LapSource): Lap source type
- `deleted` (boolean): True if record should not be counted in results calculations

`Database.LapSource` describes the method used to enter a lap into the database:
- `LapSource.REALTIME`: Lap added by (hardware) interface in real time
- `LapSource.MANUAL`: Lap added manually by user in UI
- `LapSource.RECALC`: Lap added after recalculation (marshaling) or RSSI data
- `LapSource.AUTOMATIC`: Lap added by other automatic process
- `LapSource.API`: Lap added by API (plugin)

#### db.laps
_Read only_
All lap records. Returns `list[SavedRaceLap]`.

#### db.laps_by_pilotrun(run_id)
Lap records matching the provided pilot run ID. Returns `list[SavedRaceLap]`.
- `run_id` (int): ID of pilot run used to retrieve laps


### Options
Options are settings that apply to a server globally.

Options are stored with the `GlobalSettings` class, which has the following properties:
- `id` (int): Internal identifier
- `option_name` (string): name of option
- `option_value` (string): value of option

#### db.options
_Read only_
All options. Returns `list[GlobalSettings]`.

#### db.option(name, default=False, as_int=False)
Value of option with the provided name. Returns the option value.
- `name` (string): name of option to retrieve
- `default` _(optional)_ (string): Value to return if option does not exist
- `as_int` _(optional)_ (boolean): Return value as integer instead of string

#### db.option_set(name, value)
Set value for the option with provided name. No return value.
- `name` (string): name of option to alter
- `value` (string): new value for option

#### db.options_reset()
Delete all options. No return value.


## Data input/output

View and import/export data from the database via registered `DataImporter` and `DataExporter`. See [Data Exporters](Plugins.md#data-exporters) and [Data Importers](Plugins.md#data-importers).
These methods are accessed via `RHAPI.io` 

### All Properties and Methods

#### io.exporters
_Read only_
All registered exporters. Returns `list[DataExporter]`.

#### io.run_export(exporter_id)
Run selected exporter. Returns output of exporter or `False` if error.
- `exporter_id` (string): identifier of exporter to run

#### io.importers
_Read only_
All registered importers. Returns `list[DataImporter]`.

#### io.run_import(importer_id, data, import_args=None)
Run selected importer on supplied `data`. Returns output of importer or `False` if error.
- `importer_id` (string): identifier of importer to run
- `data` (any): data to import
- `import_args` _(optional)_ (): arguments passed to the importer, overrides defaults


## Heat Generation

View and Generate heats via registered `HeatGenerator`. See [Heat Generators](Plugins.md#heat-generators).
These methods are accessed via `RHAPI.heatgen` 

### All Properties and Methods

#### heatgen.generators
_Read only_
All registered generators. Returns `list[HeatGenerator]`.

#### heatgen.generate(generator_id, generate_args)
Run selected generator, creating heats and race classes as needed. Returns output of generator or `False` if error.
- `generator_id` (string): identifier of generator to run
- `generate_args` (dict): arguments passed to the generator, overrides defaults



## Class Ranking

View registered `RaceClassRankMethods`.
These methods are accessed via `RHAPI.classrank` 

### All Properties and Methods

#### classrank.methods
_Read only_
All registered class ranking methods. Returns `dict` with the following format:
- `name`: `RaceClassRankMethod`



## Race Points

View registered `RacePointsMethods`.
These methods are accessed via `RHAPI.points` 

### All Properties and Methods

#### points.methods
_Read only_
All registered race points methods. Returns `dict` with the following format:
- `name`: `RacePointsMethod`



## LED

Activate and manage connected LED displays via registered `LEDEffects`.
These methods are accessed via `RHAPI.led` 

### All Properties and Methods

#### led.enabled
_Read only_
Returns True if LED system is enabled.

#### led.effects
_Read only_
All registered LED effects. Returns `list[LEDEffects]`.

#### led.effect_by_event(event)
LED effect assigned to event. Returns `LEDEffect` or None if event does not exist
- `event` (string): event to retrieve effect from

#### led.effect_set(event, name)
Assign effect to event. Returns boolean success value.
- `event` (string): event to assign
- `name` (string): effect to assign to event

#### led.clear
Clears LEDs. No return value.

#### led.display_color(seat_index, from_result=False)
Color of seat in active race. Returns `Color`.
- `seat_index` (int): Seat number
- `from_result` _(optional)_ (boolean): True to use previously active (cached) race data

#### led.activate_effect(args)
Immediately activate an LED effect. **Should usually be called asynchronously with `gevent.spawn()`.**
- `args` (dict): Must include `handler_fn` to activate; other arguments are passed to handler



## Video Receivers

View and manage connected Video Receiver devices.
These methods are accessed via `RHAPI.vrxcontrol` 

**Notice:** The vrx control specification is expected to be modified in future versions. Please consider this while developing plugins.

### All Properties and Methods

#### vrxcontrol.enabled
_Read only_
Returns True if VRx control system is enabled.

#### vrxcontrol.status
_Read only_
Returns status of VRx control system.

#### vrxcontrol.devices
_Read only_
Returns list of attached VRx control devices.

#### vrxcontrol.kill
Shuts down VRx control system.

#### vrxcontrol.devices_by_pilot(seat, pilot_id)
List VRx control deviced connected with a specific pilot.
- `seat` (int): seat number
- `pilot_id` (int): ID of pilot



## Active Race

View and manage the currently active race.
These methods are accessed via `RHAPI.race` 

### All Properties and Methods

#### race.pilots
_Read only_
Pilot IDs, indexed by seat. Returns `list[int]`.
To change pilots, adjust the corresponding heat (identified by `race.heat`).

#### race.teams
_Read only_
Team of each pilot, indexed by seat. Returns `list[string]`.
To change teams, adjust the corresponding pilot (identified by matching seat index in `race.pilots`).

#### race.slots
_Read only_
Total number of seats/slots. Returns `int`.

#### race.seat_colors
_Read only_
Active color for each seat, indexed by seat. Returns `list[Color]`.

#### race.update_colors()
_Read only_
Loads color set into current race based on color mode and values in database. No return value.

#### race.heat
_Read/write_
ID of assigned heat (`int` or `None`). `None` is practice mode.
To change active heat options, adjust the assigned heat.

#### race.frequencyset
_Read/write_
ID of current frequency set (`int`).
To change active frequency set options, adjust the assigned frequency set.

#### race.raceformat
_Read/write_
Active race format object. Returns `RaceFormat`, or `None` if timer is in secondary mode.
To change active format options, adjust the assigned race format.

#### race.status
_Read only_
Current status of system. Returns `RaceStatus`.

`RHRace.RaceStatus` describes the current state:
- `RaceStatus.READY`: Ready to start a new race, no race running
- `RaceStatus.STAGING`: System is staging, race begins imminently
- `RaceStatus.RACING`: Racing is underway
- `RaceStatus.DONE`: System no longer listening for lap crossings, race results must be saved or discarded

#### race.stage_time_internal
_Read only_
Internal (monotonic) timestamp of race staging start time. Returns `int`

#### race.start_time
_Read only_
System timestamp of race start time. Returns `datetime`. 

#### race.start_time_internal
_Read only_
Internal (monotonic) timestamp of race start time. Is a future time during staging. Returns `int`.

#### race.end_time_internal
_Read only_
Internal (monotonic) timestamp of race end time. Invalid unless `race.status` is `DONE`. Returns `int`.

#### race.seats_finished
_Read only_
Flag indicating whether pilot in a seat has completed all laps. Returns `dict` with the format `id` (int):`value` (boolean).

#### race.laps
_Read only_
Calculated lap results. Returns `dict`.

#### race.any_laps_recorded
_Read only_
Whether any laps have been recorded for this race. Returns `boolean`.

#### race.laps_raw
_Read only_
All lap data. Returns `list[dict]`.

#### race.laps_active_raw(filter_late_laps=False)
All lap data, removing deleted laps. Returns `list[dict]`.
- `filter_late_laps` _(optional)_: Set `True` to also remove laps flagged as late.

#### race.lap_add(seat_index, timestamp)
Add a lap record to the current race. Laps must be entered sequentially. No return value.
- `seat_index` (int): seat number on which to add lap
- `timestamp` (int): timestamp of lap to add, in server monotonic time

#### race.results
_Read only_
Calculated race results. Returns `dict`.

#### race.team_results
_Read only_
Calculated race team results. Returns `dict`, or `None` if not in team mode.

#### race.win_status
_Read only_
True if a winner has been declared. Returns `boolean`.

#### race.race_winner_name
_Read only_
Callsign of race winner, if declared. Returns `str`, or `None`.

#### race.race_winner_phonetic
_Read only_
Phonetic of race winner, if declared. Returns `str`, or `None`.

#### race.race_winner_lap_id
_Read only_
Lap count of race winner, if declared. Returns `int`, or `None`.

#### race.race_winner_pilot_id
_Read only_
Pilot database ID of race winner, if declared. Returns `int`, or `None`.

#### race.prev_race_winner_name
_Read only_
Callsign of previous race winner, if declared. Updates upon race save. Returns `str`, or `None`.

#### race.prev_race_winner_phonetic
_Read only_
Phonetic of previous race winner, if declared. Updates upon race save.. Returns `str`, or `None`.

#### race.prev_race_winner_pilot_id
_Read only_
Pilot database ID of previous race winner, if declared. Updates upon race save. Returns `int`, or `None`.

#### race.race_leader_lap
_Read only_
Lap count of current race leader. Returns `int`, or `None`.

#### race.race_leader_pilot_id
_Read only_
Pilot database ID of current race leader. Returns `int`, or `None`.

#### race.scheduled
_Read only_
Internal (monotonic) timestamp of scheduled race staging start time. Returns `int`, or `None` if race is not scheduled. 

#### race.schedule(sec_or_none, minutes=0)
Schedule race with a relative future time offset. Fails if `race.status` is not `READY`. Cancels existing schedule if both values are falsy. Returns boolean success value.
- `sec_or_none`: seconds ahead to schedule race
- `minutes` _(optional)_: minutes ahead to schedule race

#### race.stage()
Begin race staging sequence. May fail if `race.status` is not `READY`. No return value.

#### race.stop(doSave=False)
Stop race. No return value.
- `doSave` _(optional)_: run race data save routines immediately after stopping

#### race.save()
Save laps and clear race data. May activate heat advance and other procedures. No return value.

#### race.clear()
Clear laps and reset `race.status` to `READY`. Fails if `race.status` is `STAGING` or `RACING`—stop race before using. No return value.



## Event Results

View result data for all races, heats, classes, and event totals.
These methods are accessed via `RHAPI.eventresults` 

### All Properties and Methods

#### eventresults.results
_Read only_
Calculated cumulative results. Returns `dict`.



## Language and Translation

View and retrieve loaded translation strings.
These methods are accessed via `RHAPI.language` 

### All Properties and Methods

#### language.languages
_Read only_
List of available languages. Returns `list[string]`.

#### language.dictionary
_Read only_
Full translation dictionary of all loaded languages. Returns `dict`.

#### language.\_\_(text, domain='')
Translate `text`. Returns translated `string`, or `text` if not possible.
-`text` (string): Input to translate
-`domain` _(optional)_ (string): Language to use, overriding system setting



## Hardware Interface

View information provided by the harware interface layer.
These methods are accessed via `RHAPI.interface` 

### All Properties and Methods

#### interface.seats
_Read only_
Hardware interface information. Returns `list[Node]`.



## Persistent Configuration

View information stored in server configuration and persistent (non-event, non-database) storage. Data is organized in sections and then by key. You may register custom sections and store data in them, which is kept persistently and outside of the event database. These methods are accessed via `RHAPI.config` 

### All Properties and Methods

#### config.register_section(section):
Registers a custom data section and allows data to be stored and retrieved. Use during `initialize()`. No return value.
- `section` (string): name of section item is within

#### config.get_all:
_Read only_
Returns the entire current configuration set.

#### config.get(section, name, as_int=False):
Value of item in section with the provided name. Returns the option value.
- `section` (string): name of section item is within
- `name` (string): name of option to retrieve
- `as_int` _(optional)_ (boolean): Return value as integer instead of string

#### config.set(section, name, value):
	return self._racecontext.serverconfig.set_item(section, item, value)
Set value for the item with provided name in section. No return value.
- `section` (string): name of section item is within
- `name` (string): name of option to alter
- `value` (string): new value for option



## Sensors Interface

View data collected by environmental sensors such as temperature, voltage, and current.
These methods are accessed via `RHAPI.sensors` 

### All Properties and Methods

#### sensors.sensors_dict
_Read only_
All sensor names and data. Returns `dict` of `name`(string):`Sensor`.

#### sensors.sensor_names
_Read only_
List of available sensors. Returns `list[string]`.

#### sensors.sensor_objs
_Read only_
List of sensor data. Returns `list[Sensor]`.

#### sensors.sensor_obj(name)
Individual sensor data. Returns `Sensor`.
- `name` (string): Name of sensor to retrieve



## Server State

Information and functions relating to server state.
These methods are accessed via `RHAPI.server` 

### All Properties and Methods

#### server.enable_heartbeat_event()
When enabled, each time the server heartbeat function runs a `Evt.HEARTBEAT` event will be triggered. No return value.

#### server.info
_Read only_
Server information. Returns `dict`.

#### server.plugins
_Read only_
Currently loaded plugins. Returns `list[plugin]`.

#### server.program_start_epoch_time
_Read only_
Time this server was started, in epoch milliseconds. Returns `float`.

#### server.program_start_mtonic
_Read only_
Time this server was started, in monotonic seconds. Returns `float`.

#### server.mtonic_to_epoch_millis_offset
_Read only_
Conversion offset between monotonic seconds and epoch milliseconds. Returns `float`.

#### server.program_start_epoch_formatted
_Read only_
Time this server was started, in epoch milliseconds, displayed without decimals. Returns `string`.

#### server.program_start_time_formatted
_Read only_
Time this server was started, formatted for readability. Returns `string`.

#### server.monotonic_to_epoch_millis(secs)
Convert time value from server monotonic seconds to epoch milliseconds, using this server's conversion offset. Returns `float`.
- `secs` (int|float): time in monotonic seconds

#### server.epoch_millis_to_monotonic(ms)
Convert time value from epoch milliseconds to server monotonic seconds, using this server's conversion offset. Returns `float`.
- `ms` (int|float): time in epoch milliseconds

#### server.seat_color_defaults:
_Read only_
List of sensor data. Returns `list[Sensor]`.

#### server.program_dir:
_Read only_
System path to server instance. Returns `string`.

#### server.data_dir:
_Read only_
System path to user data directory. Returns `string`.


## Utilitites

Helper functions and utilities for data handling. 
These methods are accessed via `RHAPI.utils` 

### All Properties and Methods

#### utils.format_time_to_str(millis, time_format=None):
Convert milliseconds converted to formatted time (00:00.000). Returns `string`.
- `time_format` _(optional)_ (string): Time format string, overriding user-specified format 

#### utils.format_split_time_to_str(millis, time_format=None):
Convert milliseconds to formatted time with leading zeros removed (0:00.000). Returns `string`.
- `time_format` _(optional)_ (string): Time format string, overriding user-specified format 

#### utils.format_phonetic_time_to_str(millis, time_format=None):
Convert milliseconds to formatted phonetic callout time (0 0.0). Returns `string`.
- `time_format` _(optional)_ (string): Time format string, overriding user-specified format 

#### utils.generate_unique_name(desired_name, other_names):
Generate unique name within a naming context. Returns `desired_name` if possible, otherwise adds an incremental token: "Name", "Name 2". Returns `string`.
- `desired_name` (string): desired name 
- `other_names` (list[string]): list of names to compare against and avoid 

#### utils.generate_unique_name_from_base(base_name, other_names):
Generate unique name within a naming context. Always adds an incremental token to `base_name`: "Name 1", "Name 2". Returns `string`.
- `base_name` (string): desired base name 
- `other_names` (list[string]): list of names to compare against and avoid 

#### utils.color_hsl_to_hexstring(h, s, l):
Convert HSL color values to a hexadecimal string. Returns `string`.
- `h` (int|float): hue component, from 0 to <360
- `s` (int|float): saturation component, from 0 to 100
- `l` (int|float): luminance component, from 0 to 100
    
#### utils.color_hexstring_to_int(hex_color):
Convert hexadecimal string color to packed int. Accepts strings with or without "#" prefix. Returns `int`.
- `hex_color` (string): hexadecimal color string to convert



## Filters

Alter the output of functions and processes at specified hooks.
These methods are accessed via `RHAPI.filters` 

For example, the `Flt.EMIT_PHONETIC_DATA` hook runs just before lap announcement data is sent to the frontend. Adding a filter to this hook allows the filter to alter the text that is read aloud.

### All Properties and Methods

#### filters.add(hook, name, fn, priority=200):
Add a new filter function to an existing hook. The filter will be run when the hook is triggered.
- `hook` (Flt|string): Hook to attach this filter to 
- `name` (string): Internal identifier for this filter
- `fn` (function): Function to run when the hook is triggered 
- `priority` _(optional)_ (int): Order in which this filter will run among all attached to this hook

#### filters.remove(hook, name):
Remove a filter from a hook.
- `hook` (Flt|string): Hook from which filter to remove is attached
- `name` (string): Internal identifier of filter to remove

#### filters.run(hook, data):
Run filters attached to specified hook.
- `hook` (Flt|string): Hook on which filters will be called
- `data` (any): Data supplied to filters attached to hook
