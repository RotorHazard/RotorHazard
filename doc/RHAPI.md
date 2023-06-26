# RHAPI

- [Introduction](#introduction)
- [User Interface Helpers](#user-interface-helpers-ui)
- [Data Fields](#data-fields-fields)
- [Database Access](#database-access-db)
- [Data input/output](#data-input-output-io)
- [Heat Generation](#heat-generation-heatgen)
- [Class Ranking Methods](#class-ranking-methods-classrank)
- [Race Points Methods](#race-points-methods-points)
- [LED](#led-led)
- [Video Receivers](#video-receivers-vrxcontrol)
- [Active Race](#active-race-race)
- [Event Results](#event-results-eventresults)
- [Language and Translation](#language-and-translation-language)
- [Hardware Interface](#hardware-interface-interface)
- [Sensors Interface](#sensors-interface-sensors)


## Introduction

Most plugin interfaces provide access to `RHAPI`, an object providing a wide range of properties and methods across RotorHazard's internal systems. Using RHAPI, one can manipulate nearly every facet of a race event and RotorHazard's behavior.

### API Version

The API version can be read from the `API_VERSION_MAJOR` and `API_VERSION_MINOR` properties.

### Language translation shortcut

The language translation function can be accessed directly via `RHAPI.__()` in addition to its location within `RHAPI.language`.



## User Interface Helpers: `ui`

Interact with RotorHazard's frontend user interface.
These methods are accessed via `RHAPI.ui` 

### UI Panels

Add custom UI panels to RotorHazard's frontend pages. Panels may contain Options and Quickbuttons.

#### panels
_Read only_
Provides a list of registered UI panels.

#### register_panel(name, label, page, order=0)
Register a UI panel and assign it to a page.

- `name` (string): Internal identifier for this panel
- `label` (string): Text used as visible panel header
- `page` (string): Page to add panel to; one of "format", "settings"
- `order` _optional_ (int): Not yet implemented 


### Quickbuttons

Provides a simple interface to add a UI button and bind it to a function. Quickbuttons appear on assigned UI panels.

#### register_quickbutton(panel, name, label, function)
Register a Quickbutton and assign it to a UI panel.

- `panel` (string): `name` of panel previously registered with `ui.register_panel`
- `name` (string): Internal identifier for this quickbutton
- `label` (string): Text used for visible button label
- `function` (callable): Function to run when button is pressed


### Pages

Add custom pages to RotorHazard's frontend with Flask Blueprints.

#### blueprint_add(blueprint)
Adds a [Flask Blueprint](https://flask.palletsprojects.com/blueprints/) which can be used to provide access to custom pages/URLs.

- `blueprint` (blueprint): Flask Blueprint object

### UI Messages

Send messages to RotorHazard's frontend.

#### message_speak(message)
Sends a message which is parsed by the text-to-speech synthesizer.

- `message` (string): Text of message to be spoken

#### message_notify(message)
Sends a message which appears in the message center and notification bar.

- `message` (string): Text of message to display

#### message_alert(message)
Sends a message which appears as a pop-up alert.

- `message` (string): Text of message to display



## Data Fields: `fields`

Create and access new data structures.
These methods are accessed via `RHAPI.fields` 


### Options
Options are simple storage variables which persist to the database and can be presented  to users through frontend UI. Each option takes a single value.

#### options
_Read only_
Provides a list of options registered by plugins. Does not include built-in options.

#### register_option(field, panel=None, order=0)
Register an option and optioanlly assign it to be desiplayed on a UI panel.

- `field` (UIField): See [UI Fields](Plugins.md#ui-fields)
- `panel` _optional_ (string): `name` of panel previously registered with `ui.register_panel`
- `order` _optional_ (int): Not yet implemented


### Pilot Attributes

Pilot Attributes are simple storage variables which persist to the database and can be presented to users through frontend UI. Pilot Attribute values are unique to/stored individually for each pilot.

#### pilot_attributes
_Read only_
Provides a list of registered pilot attributes.

#### register_pilot_attribute(field)
Register an attribute to be displayed in the UI or otherwise made accessible to plugins.

- `field` (UIField): See [UI Fields](Plugins.md#ui-fields)



## Database Access: `db`

Read and modify database values.
These methods are accessed via `RHAPI.db` 

### Global
Properties and methods spanning the entire stored event.

#### event_results
_Read only_
Returns cumulative totals for all saved races.

#### clear_all()
Resets database to default state, clearing all pilots, heats, race classes, races, race formats, frequency sets, and options.

### Pilots
A pilot is an individual participant. In order to participate in races, pilots can be assigned to multiple heats.

#### pilots
_Read only_
Returns all pilot records as a list.

#### pilot_by_id(pilot_id)
Returns a single pilot record. Does not include custom attributes.
- `pilot_id` (int): ID of pilot record to retrieve

#### pilot_attributes(pilot_or_id)
Returns all custom attributes assigned to pilot.
- `pilot_or_id` (pilot|int): Either the pilot object or the ID of pilot

#### pilot_attribute_value(pilot_or_id, name, default_value=None)
Returns a single custom attribute assign to pilot.
- `pilot_or_id` (pilot|int): Either the pilot object or the ID of pilot
- `name` (string): attribute to retrieve
- `default_value` _(optional)_: value to return if attribute does not exist

#### pilot_add(name=None, callsign=None, phonetic=None, team=None, color=None)
Add a new pilot to the database.
- `name` _(optional)_ (string): Name for new pilot
- `callsign` _(optional)_ (string): Callsign for new pilot
- `phonetic` _(optional)_ (string): Phonetic spelling for new pilot callsign
- `team` _(optional)_ (string): Team for new pilot
- `color` _(optional)_ (string): Color for new pilot

#### pilot_alter(pilot_id, name=None, callsign=None, phonetic=None, team=None, 
Alter pilot data.
- `pilot_id` (int): ID of pilot to alter
- `name` _(optional)_ (string): New name for pilot
- `callsign` _(optional)_ (string): New callsign for pilot
- `phonetic` _(optional)_ (string): New phonetic spelling of callsign for pilot
- `team` _(optional)_ (string): New team for pilot
- `color` _(optional)_ (string): New color for pilot
- `attributes` _(optional)_ (list[dict]): Attributes to alter, attribute values assigned to respective keys

#### pilot_delete(pilot_or_id)
Delete pilot record.
- `pilot_or_id` (int): ID of pilot to delete 

#### pilots_clear
Delete all pilot records.

### Heats
Heats are collections of pilots upon which races are run. A heat may first be represented by a heat plan which defines methods for assigning pilots. The plan must be seeded into pilot assignments in order for a race to be run.

#### heats
_Read only_
Returns all heat records as a list.

#### heat_by_id(heat_id)
Returns a single heat record.
- `heat_id` (int): ID of heat record to retrieve

#### heats_by_class(raceclass_id)
Returns all heat records associated with a specific class.
- `raceclass_id` (int): ID of raceclass used to retrieve heats

#### heat_results(heat_or_id)
Returns the calculated summary result set for all races associated with this heat
- `heat_or_id` (int|heat): Either the heat object or the ID of heat

#### heat_max_round(heat_id)
Returns the highest-numbered race round recorded for selected heat
- `heat_id` (int): ID of heat

#### heat_add(name=None, raceclass=None, auto_frequency=None)
Add a new heat to the database.
- `name` _(optional)_ (string): Name for new heat
- `raceclass` _(optional)_ (int): Raceclass ID for new heat
- `auto_frequency` _(optional)_ (boolean): Whether to enable auto-frequency

#### heat_duplicate(source_heat_or_id, dest_class=None)
Duplicate a heat record.
- `source_heat_or_id` (int|heat): Either the heat object or the ID of heat to copy from
- `dest_class` _(optional)_ (int): Raceclass ID to copy heat into

#### heat_alter(heat_id, name=None, raceclass=None, auto_frequency=None, status=None)
Alter heat data.
- `heat_id` (int): ID of heat to alter
- `name` _(optional)_ (string): New name for heat
- `raceclass` _(optional)_ (int): New raceclass ID for heat
- `auto_frequency` _(optional)_ (boolean): New auto-frequency setting for heat
- `status` _(optional)_ (HeatStatus): New status for heat

#### heat_delete(heat_or_id)
- `heat_or_id` (int|heat): ID of heat to delete

#### heats_clear
Delete all heat records.

### Heat &rarr; Slots
Slots are data structures containing a pilot assignment or assignment method. Heats contain one or more Slots corresponding to pilots who may participate in the Heat. When a heat is calculated, the `method` is used to reserve a slot for a given pilot. Afterward, `pilot` contains the ID for which the space is reserved. A Slot assignment is only a reservation, it does not mean the pilot has raced regardless of heat `status`.

#### slots
_Read only_
Returns all slot records as a list.

#### slots_by_heat(heat_id)
Returns slot records associated with a specific heat as a list.
- `heat_id` (int): ID of heat used to retrieve slots

#### slot_alter(slot_id, pilot=None, method=None, seed_heat_id=None, seed_raceclass_id=None, seed_rank=None)
Alter slot data.
- `slot_id` (int): ID of slot to alter
- `pilot` _(optional)_ (int): New ID of pilot assigned to slot
- `method` _(optional)_ (ProgramMethod): New seeding method for slot
- `seed_heat_id` _(optional)_ (): New heat ID to use for seeding
- `seed_raceclass_id` _(optional)_ (int): New raceclass ID to use for seeding
- `seed_rank` _(optional)_ (int): New rank value to use for seeding

`ProgramMethod` is one of `ProgramMethod.NONE`, `ProgramMethod.ASSIGN`, `ProgramMethod.HEAT_RESULT` or `ProgramMethod.CLASS_RESULT`. With `NONE`, most other fields are ignored. Only use `seed_heat_id` with `HEAT_RESULT`, and `seed_raceclass_id` with `CLASS_RESULT`, otherwise the assignment is ignored.

Import `ProgramMethod` with:
`from Database import ProgramMethod`

#### slot_alter_fast(slot_id, pilot=None, method=None, seed_heat_id=None, seed_raceclass_id=None, seed_rank=None
Like `slot_alter`, but intended to be used when many alterations need done at once. Does not check for some types of invalid input. Does not trigger events, clear results, or update cached data. These operations must be done manually if required.
- `slot_id` (int): ID of slot to alter
- `pilot` _(optional)_ (int): New ID of pilot assigned to slot
- `method` _(optional)_ (ProgramMethod): New seeding method for slot
- `seed_heat_id` _(optional)_ (): New heat ID to use for seeding
- `seed_raceclass_id` _(optional)_ (int): New raceclass ID to use for seeding
- `seed_rank` _(optional)_ (int): New rank value to use for seeding


### Race Classes

#### raceclasses
_Read only_
#### raceclass_by_id(raceclass_id)
raceclass_id
#### raceclass_add(name=None, description=None, raceformat=None, win_condition=None, 
name=None, description=None, raceformat=None, win_condition=None,rounds=None, heat_advance_type=None)
#### raceclass_duplicate(source_class_or_id)
source_class_or_id
#### raceclass_alter(raceclass_id, name=None, description=None, raceformat=None, win_
raceclass_id, name=None, description=None, raceformat=None, wincondition=None, rounds=None, heat_advance_type=None, rank_settings=None)
#### raceclass_results(raceclass_or_id)
raceclass_or_id
#### raceclass_ranking(raceclass_or_id)
raceclass_or_id
#### raceclass_delete(raceclass_or_id)
raceclass_or_id
#### raceclasses_clear

### Race Formats

#### raceformats
_Read only_
#### raceformat_by_id(format_id)
format_id
#### raceformat_add(name=None, unlimited_time=None, race_time_sec=None, lap_grace_
name=None, unlimited_time=None, race_time_sec=None, lap_gracesec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None)
#### raceformat_duplicate(source_format_or_id)
source_format_or_id
#### raceformat_alter(raceformat_id, name=None, unlimited_time=None, race_time_sec=None, 
raceformat_id, name=None, unlimited_time=None, race_time_sec=None,lap_grace_sec=None, staging_fixed_tones=None, staging_delay_tones=None, start_delay_min_ms=None, start_delay_max_ms=None, start_behavior=None, win_condition=None, number_laps_win=None, team_racing_mode=None, points_method=None, points_settings=None)
#### raceformat_delete(raceformat_id)
raceformat_id
#### raceformats_clear

### Frequency Sets

#### frequencysets
_Read only_
#### frequencyset_by_id(set_id)
set_id
#### frequencyset_add(name=None, description=None, frequencies=None, enter_ats=None, exit
name=None, description=None, frequencies=None, enter_ats=None, exi_ats=None)
#### frequencyset_duplicate(source_set_or_id)
source_set_or_id
#### frequencyset_alter(set_id, name=None, description=None, frequencies=None, enter_
set_id, name=None, description=None, frequencies=None, enterats=None, exit_ats=None)
#### frequencyset_delete(set_or_id)
set_or_id
#### frequencysets_clear

### Saved Races

#### races
_Read only_
#### race_by_id(race_id)
race_id
#### race_by_heat_round(heat_id, round_number)
heat_id, round_number
#### races_by_heat(heat_id)
heat_id
#### races_by_raceclass(raceclass_id)
raceclass_id
#### race_results(race_or_id)
race_or_id
#### races_clear

### Saved Race &rarr; Pilot Runs

#### pilotruns
_Read only_
#### pilotrun_by_id(run_id)
run_id
#### pilotrun_by_race(race_id)
race_id

### Saved Race &rarr; Pilot Run &rarr; Laps

#### laps
_Read only_
#### laps_by_pilotrun(run_id)
run_id

### Options

#### options
_Read only_
#### option(name, default=False, as_int=False)
name, default=False, as_int=False
#### option_set(name, value)
name, value
#### options_clear



## Data input/output: `io`

View and import/export data from the database via registered `DataImporters` and `DataExporters`.
These methods are accessed via `RHAPI.io` 

#### exporters
_Read only_
#### run_export
#### importers
_Read only_
#### run_import



## Heat Generation: `heatgen`

View and Generate heats via registered `HeatGenerators`.
These methods are accessed via `RHAPI.heatgen` 

#### generators
_Read only_
#### run_export(generator_id, generate_args)
generator_id, generate_args



## Class Ranking Methods: `classrank`

View registered `RaceClassRankMethods`.
These methods are accessed via `RHAPI.classrank` 

#### methods
_Read only_



## Race Points Methods: `points`

View registered `RacePointsMethods`.
These methods are accessed via `RHAPI.points` 

#### methods
_Read only_



## LED: `led`

Activate and manage connected LED displays via registered `LEDEffects`.
These methods are accessed via `RHAPI.led` 

#### enabled
_Read only_
#### effects
_Read only_
#### effect_by_event(event)
event
#### effect_set(event, name)
event, name
#### clear
#### display_color(seat_index, from_result=False)
seat_index, from_result=False
#### activate_effect(args)
args



## Video Receivers: `vrxcontrol`

View and manage connected Video Receiver devices.
These methods are accessed via `RHAPI.vrxcontrol` 

#### enabled
_Read only_
#### status
_Read only_
#### devices
_Read only_
#### kill
#### devices_by_pilot(seat, pilot_id)
seat, pilot_id



## Active Race: `race`

View and manage the currently active race.
These methods are accessed via `RHAPI.race` 

#### pilots
_Read only_
#### teams
_Read only_
#### slots
_Read only_
#### seat_colors
_Read only_
#### heat
_Read only_
#### frequencyset
_Read only_
#### raceformat
_Read only_
#### status
_Read only_
#### stage_time_internal
_Read only_
#### start_time
_Read only_
#### start_time_internal
_Read only_
#### end_time_internal
_Read only_
#### seats_finished
_Read only_
#### laps
_Read only_
#### any_laps_recorded
_Read only_
#### laps_raw
_Read only_
#### laps_active_raw(filter_late_laps=False)
filter_late_laps=False
#### results
_Read only_
#### team_results
_Read only_
#### scheduled
_Read only_

#### schedule(sec_or_none, minutes=0)
sec_or_none, minutes=0
#### stage
#### stop(doSave=False)
doSave=False



## Event Results: `eventresults`

View or clear result data for all races, heats, classes, and event totals.
These methods are accessed via `RHAPI.eventresults` 

#### results
_Read only_
#### results_clear



## Language and Translation: `language`

View and retrieve loaded translation strings.
These methods are accessed via `RHAPI.language` 

#### languages
_Read only_
#### dictionary
_Read only_
#### \_\_(text, domain='')
text, domain=''



## Hardware Interface: `interface`

View information provided by the harware interface layer.
These methods are accessed via `RHAPI.interface` 

#### seats
_Read only_



## Sensors Interface: `sensors`

View data collected by environmental sensors such as temperature, voltage, and current.
These methods are accessed via `RHAPI.sensors` 

#### sensors_dict
_Read only_
#### sensor_names
_Read only_
#### sensor_objs
_Read only_
#### sensor_obj(name)
name
