# RotorHazard Race Timer User Guide

- [Initial Setup](#initial-setup)
    - [Hardware and Software Setup](#hardware-and-software-setup)
    - [Connect to the Server](#connect-to-the-server)
- [Pages](#pages)
    - [Home](#home)
    - [Event](#event)
    - [Results](#results)
    - [Current](#current)
    - [Format](#format)
    - [Settings](#settings)
    - [Run](#run)
    - [Marshal](#marshal)

## Initial Setup

### Hardware and Software Setup
Follow the instructions here if not done already:<br>
[Hardware Setup](Hardware%20Setup.md)<br>
[Software Setup](Software%20Setup.md)<br>
[RF shielding](Shielding%20and%20Course%20Position.md)

### Connect to the Server
A computer, phone or tablet may be used to interact with the race timer by launching a web browser and entering the IP address of the Raspberry Pi. The Raspberry Pi may be connected using an ethernet cable, or to an available WiFi network. If the IP address of the Pi is not known, it may be viewed using the terminal command "ifconfig", and it can configured to a static value on the Pi desktop via the "Network Preferences." If the Pi is connected to a WiFi network, its IP address may be found in the 'Clients' list on the admin page for the network's router.

In the web browser, type in the IP address of for the race timer and the port value you set in the config file. (You may leave off the :port if set to 80 or [port forwarding from 80](Software%20Setup.md#enable-port-forwarding) is enabled.)

```
XXX.XXX.XXX.XXX:5000
```

Once the page is successfully displayed, it may be bookmarked in the browser. Pages reserved for the race director ("Admin / Settings") are password protected with the username and password specified in the config file.

## Pages

### Home

This page displays the event name and description, along with a set of buttons to various other pages.


### Event

This public page displays the current class setup (if applicable), and a summary of pilots and their heats with channel assignment.


### Results

This public page will display results and calculated statistics of all previously saved races, organized into collapsible panels. Aggregate results are displayed for each heat with multiple rounds, each class, and the entire event.


### Current

This page displays information about the currently running race, including real-time race time, pilot lap times and leaderboard. It automatially updates with the event, and is suitable for projecting to a prominently displayed screen.

In the Audio Control section, the user can select whether any one pilot, all pilots, or no pilots will have laps announced. In this way, a pilot might elect to hear only their own laps announced. A user can also adjust the voice, volume, rate, and pitch of these announcements.


### Format

This page is for adjusting event-specific parameters.

#### Event
Event information is displayed to users, such as on the home page when users first connect to the system or at the top of the Results page.

_Consecutive Laps Base_ sets the number of laps which RotorHazard calculates for its Consecutive Laps race formats and results.

_Minimum Lap Time_ and _Minimum Lap Behavior_ change how RotorHazard highlights or discards short passes. _Minimum Lap Time_ changes the threshold under which will activate the _Minimum Lap Behavior_. Use the "discard" behavior with caution, as this will eliminate data that may have been valid.

#### Pilots
Add an entry for each pilot that will race. The system will announce pilots based on their callsign. A phonetic spelling for a callsign may be used to influence the voice callouts; it is not required.

_Pilot Sort_ affects how pilot selectors in the RotorHazard interface will be sorted. Reloading the page may be necessary to see the effects.

_Color Mode_ affects how RotorHazard assigns colors to pilots in each race.
- "Seat": assigns a color based on which seat a pilot is slotted into for the race
- "Pilot": assigns a color based on the color value chosen in the pilot list
- "Frequency": assigns a color based on the frequency selected for the seat, per the color standard established by Betaflight

#### Classes and Heats
Classes are groups of heats and races that share common characteristics. Each class will have its own results and ranking calculated separately from others. Classes are not required for events but are generally recommended. Class results can be useful for seeding multiple events phases, such as qualifying into finals. Create a class (if desired) and add heats to it.

Classes may be given a name and description in addition to other properties:
- _Race Format_: if selected, this race format is force-applied to all races in the class
- _Ranking_: method by which this class is ranked. May be extended by plugins
- _Rounds_: number of rounds after which RotorHazard considers the heat to be done; leave at 0 to continue running this class until another is manually chosen
- _Advance Heat_: determines whether RotorHazard will automatically move to the next heat when a race in this class concludes

Heats are groups of pilots racing together simultaneously. Heats contain slots where you assign pilots who will race. Optional heat names can be added if desired. The number of slots available is determined by the hardware configuration of the timer. Each slot has a mode and assignment criteria. Heat slots may be set to *None* to prevent a pilot from being assigned.
- "Pilot": directly assigns a pilot to this race slot
- "Heat": Use the results of another heat when seeding this heat. When selected, choose the heat to seed from and the ranking position that will be used
- "Class": Use the results of a class when seeding this heat. When selected, choose the class to seed from and the ranking position that will be used

If "Auto Frequency" is on, slots are not assigned to seats (and frequencies) until a heat is seeded. This is strongly recommended if the "Heat" or "Class" methods are used.

If any of the slots uses either "Heat" or "Class" method, or if "Auto Frequency" is on, dynamic seeding becomes active for the heat.

A dynamically seeded heat can be in the "Plan" or "Seeded" state. A newly created heat is in the Plan state, and a race cannot be run until the heat is seeded. You may seed a heat using the "Seed Now" button, which will pull the current results from any selected heats and classes to create pilot assignments. If "Auto Frequency" is on, slots (and frequencies) are also assigned during this step. Plan heats are seeded when selected on the [Run](#run) page. If you confirm the assignments shown, the heat becomes seeded. Seeded heats that have not yet been used to run a race can be switched back to the "Plan" state using the "Revert to Plan" button. Note that seeding is not deterministic; reseeding may not produce the same results.

As you run races, classes and heats will become locked and cannot be modified. This protects saved race data from becoming invalid. You may unlock heats and classes to modify their data. If you do, you are rewriting race history for those heats and classes as if they were set up from the beginning. _If you wish to make a change to a heat going forward only and without affecting race history, duplicate the heat to create a new one._ Clearing races from the event will unlock all heats and classes.

#### Generators

Generators create classes and heats. Several generators are built into RotorHazard by default, and additional generators may be available if added by plugin.

_Generator_ selects which method to use.
_Input_ chooses which class will be used to seed the generated heats. Choose "-All Pilots-" to use every currently loaded pilot with no regard for ranking.
_Output_ selects where to place the generated results. Choose "-New Class-" to have RotorHazard create a class where the results will be placed.

If a generator has additional parameters, they will appear when the "Generate Heats" button is pressed.

- _Balanced Random Fill_: Fills heats randomly from the input pool, keeping the number of pilots in each heat as consistent as possible.
    - _Maximum pilots per heat_: Limits the total number of pilots that are drawn from the input pool for each heat; if _Auto_, will use the current number of seats which are not disabled
    - _Maximum pilots in class_: Limits the total number of pilots that are drawn from the input pool for the class, if an input class is selected
    - _Seed from rank_: Skips pilots before seeding; useful for "next 16"-type brackets
    - _Heat title suffix_: Modifies the name of generated heats
- _Ladder_: Generates ladder (sometimes called "letter") heats
    - _Advances per heat_: Number of pilots which will advance (or "bump") up to the next higher ladder heat (0 is acceptable)
    - _Seeded slots per heat_: Number of pilots which are seeded into each ladder heat from the input pool
    - _Pilots in class_: Limits the total number of pilots that are drawn from the input pool for the class, if an input class is selected
    - _Seed from rank_: Skips pilots before seeding; useful for "next 16"-type brackets
    - _Heat title suffix_: Modifies the name of generated heats
- _Ranked Fill_:
    - _Maximum pilots per heat_: Limits the total number of pilots that are drawn from the input pool for each heat; if _Auto_, will use the current number of seats which are not disabled
    - _Maximum pilots in class_: Limits the total number of pilots that are drawn from the input pool for the class, if an input class is selected
    - _Seed from rank_: Skips pilots before seeding; useful for "next 16"-type brackets
    - _Heat title suffix_: Modifies the name of generated heats
- _Regulation bracket, double elimination_:
    - _Spec_: Regulation to follow for generating brackets
    - _Seed from rank_: Skips pilots before seeding; useful for "next 16"-type brackets
- _Regulation bracket, single elimination_:
    - _Spec_: Regulation to follow for generating brackets
    - _Seed from rank_: Skips pilots before seeding; useful for "next 16"-type brackets


#### Race Formats
Race formats define how an individual race is conducted. Choose a format to adjust.

The "+" button will duplicate the current race format, and the "x" button will remove the current race format. (Once a race format is removed it cannot be recovered, but default formats may be restored from the Data Management panel.)

The race clock can count up or down as selected by _Race Clock Mode_. Use "No Time Limit" for a "First to X laps" style with a timer that counts upward from zero. Use "Fixed Time" for a timer which counts down to zero after the race starts. _Timer Duration_ is used in "Fixed Time" mode to determine race length.

During a "Fixed Time" race, _Grace Period_ is the amount of time after the race clock expires before the timer is automatically stopped. Set _Grace Period_ to "0" to stop a race immediately when time expires. If _Grace Period_ is set to "-1", the clock continues indefinitely and must be stopped manually.

Each race begins with a staging sequence. Adjust the _Prestage Tones_ value to control the length of the *prestage* phase, during which one tone will sound each second. Next is the *staging* phase, which can be a fixed or random duration. _Minimum Staging Time_ sets a fixed minimum duration for the *staging* phase. If _Random Staging Time_ is greater than zero, the timer will additionally delay randomly between zero and this value. Setting _Random Staging Time_ above zero also hides the staging clock, which will show "Ready" instead of a countdown. Choose whether tones are heard during the *staging* phase with _Staging Tones_.

##### Examples:
* A fixed "3, 2, 1, Go" countdown start:
    * _Prestage Tones_: 3
    * _Staging Tones_: (any)
    * _Minimum Staging Time_: 1.0
    * _Random Staging Time_: 0.0
* 1 prestage tone followed by a start tone within 1–5 seconds:
    * _Prestage Tones_: 1
    * _Staging Tones_: None
    * _Minimum Staging Time_: 1.0
    * _Random Staging Time_: 5.0
* 5 prestage tones followed by a random delay between 0.2 and 3.0 seconds:
    * _Prestage Tones_: 5
    * _Staging Tones_: None
    * _Minimum Staging Time_: 0.2
    * _Random Staging Time_: 2.8
* A variable number of tones between 2 and 5, then start:
    * _Prestage Tones_: 2
    * _Staging Tones_: Each Second
    * _Minimum Staging Time_: 0.2
    * _Random Staging Time_: 3.7

_A small amount of time is needed to ensure the timer has synchronized with all hardware, so there is always a short period to start a race even with all staging times set to zero._

When a pilot crosses for the first time in a race, _First Crossing_ affects how result displays and race outcomes are processed. "Hole Shot" records the race time of each pilot's first crossing as beginning their first lap. "First Lap" records the race time of each pilot's first crossing as ending their first lap. "Staggered Start" begins each pilot's own race clock their first crossing, disregarding the global race clock. "Staggered Start" is typically combined with the "No Time Limit" _Race Clock Mode_.

_Win Condition_ determines how the timer calls out the winner of the race, the information presented in the OSD and streaming display, and sort method for leaderboards. Leaderboard sorting affects the results page and heat generator.
* __Most Laps in Fastest Time__: Pilots are judged by the number of laps completed and how long it took to complete them. If there is a tie for the number of laps completed, the pilot who completed those laps in a shorter amount of time will be ranked higher.
* __Most Laps Only__: Scored only by the completed lap count. Pilots with the same lap count are tied. Use with "Fixed Time" mode for a race style before timing was reliable, or with "No Time Limit" mode to judge the greatest distance instead of shortest time.
* __Most Laps Only with Overtime__: Similar to _Most Laps in Fastest Time_, but with a "sudden death" component. When the timer expires (or the race is stopped early), if a pilot has more laps than all the others then that pilot is the winner. If there is a tie for lap count when the timer expires, the first of the tied pilots across the line is the winner.
* __First to X Laps__: The race continues until one pilot reaches the desired lap count. In this mode, the _Number of Laps to Win_ parameter is used. Typically used with the _No Time Limit_ race mode.
* __Fastest Lap__: Ignores the race progress and considers only each pilot's single fastest lap.
* __Fastest 3 Consecutive Laps__: Considers all laps a pilot has completed and uses the three consecutive laps with the fastest combined time.
* __None__: Does not declare a winner under any circumstance. Heats generated from a class with this condition will be assigned randomly.

__Team/Co-op Racing Mode__ provides access to racing modes in which pilots may compete together in groups. 

__Team Racing__ allows groups of pilots to complete as teams. The team for each pilot may be set in the 'Pilots' section. Win conditions in team racing mode differ somewhat:
* __Most Laps in Fastest Time__: Teams are judged on combined lap count of all members and how long it took to complete those laps.
* __Most Laps Only__: Teams are judged on total combined lap count of all members.
* __Most Laps Only with Overtime__: Teams are judged on total combined lap count of all members. If tied when time expires, the first team (of those tied) to add a lap becomes the winner.
* __First to X Laps__: The first team to complete the desired combined lap count is the winner.
* __Fastest Lap__: After all team members have contributed one lap, teams are judged by the average of pilots' fastest lap time.
* __Fastest 3 Consecutive Laps__: After all team members have contributed 3 laps, teams are judged by the average of pilots' fastest "three consecutive laps" time.

With _Fastest Lap_ and _Fastest 3 Consecutive Laps_, teams with differing numbers of pilots can compete together fairly.

__Co-op Racing__ allows all pilots in a race to work as a cooperative group to improve their combined performance. Pilots of varying abilities can race together, with everyone contributing and working on improving their skills. There are two versions of co-op racing, described below. In both versions, all pilots in the current heat race together as a group. In the first race, a benchmark performance is set, and in each race after that the group attempts to improve and achieve a new best performance. 

* _Co-op Fastest Time to X Laps_: The group attempts to complete the given number of laps (X) in the fastest time. When this racing format is enabled (on the 'Run' page), the current "Co-op Best Time" value will be shown in the "Race Management" section, and the value may be altered or cleared there.  

* _Co-op Most Laps in X:XX_: The group attempts to complete the most number of laps in the given race time (X:XX). When this racing format is enabled (on the 'Run' page), the current "Co-op Best # of Laps" value will be shown in the "Race Management" section, and the value may be altered or cleared there.

The "%COOP_RACE_INFO%" and "%COOP_RACE_LAP_TOTALS%" variables can be used in callouts with co-op races, see the [Event Actions](#event-actions) section for descriptions. 

#### Data Management

_Stored Data_ can be used to backup the current database (save to a file on the pi and prompt to download it) or restore events from stored data files

_Reset_ may clear races, classes, heats, pilots, and race formats

_Import_ uses plugins to extract data from files and fill event values

_Export_ uses plugins to extract event values and save to files


### Settings

This page allows changing the timer's optional settings and event setup.

#### Frequency Setup
Choose a preset or manually select frequencies for each node. Arbitrary frequency selection is possible, as is disabling a node. The IMD score for currently selected frequencies is calculated and displayed at the bottom of the panel.

Profiles contain frequencies and node tuning values. Changing this list immediately activates the selected profile, and changing current frequencies and node tuning immediately saves to the profile.

#### Sensor Tuning
See [doc/Tuning Parameters.md](Tuning%20Parameters.md) for a detailed description and tuning guide.

#### Audio Control
All audio controls are local to the browser and device where you set them, including the list of available languages, volumes, and which announcements or indicators are in use.

Voice select chooses the text-to-speech engine. Available selections are provided by the web browser and operating system.

Announcements allow the user to choose to hear each pilot's callsign, lap number, and/or lap time as they cross. The "Race Clock" announcement will periodically call out how much time has elapsed or is remaining, depending on the timer mode in the race format. "Team/Co-op Lap Total" applies when "Team Racing Mode" or "Co-op Racing Mode" is enabled, and configures whether or not the lap total for the pilot group is announced on each lap. The "On Team/Co-op Races (short call)" option will result in a short version of the callout (simply "Lap X").

Voice volume, rate, and pitch control all text-to-speech announcements. "Tone Volume" controls race start and end signals.

Indicator beeps are very short tones that give feedback on how the timer is working, and are most useful when trying to tune it. Each node is identified with a unique audio pitch. "Crossing Entered" will beep once when a pass begins, and "Crossing Exited" will beep twice rapidly when a pass is completed. "Manual Lap Button" will beep once if the "Manual" button is used to force a simulated pass.

If you select "Use MP3 Tones instead of synthetic tones" then the '.mp3' files at "src/server/static/audio" will be used to play the tones. (This is necessary on some web browsers and operating systems.)

#### Event Actions
Extend and personalize your timer's behavior by attaching *Effects* to *Events*. The timer generates an *Event* on race start, lap recorded, pilot done, etc. *Effects* are behaviors that can be triggered. Each effect may have parameters which can be configured.

For example, you might add the "Speak" effect to the "Pilot Done" event in order to call out when each pilot has completed their own laps.

* _Speak_ produces an audible voice callout
* _Message_ creates a standard text notification
* _Alert_ creates a priority (pop-up) alert message

The variables listed below may be used for the  effects.

| Variable                  | Description                                                             |
|---------------------------|-------------------------------------------------------------------------|
| %PILOT%                   | Pilot callsign                                                          |
| %HEAT%                    | Current heat name or ID value                                           |
| %ROUND%                   | Current round number                                                    |
| %ROUND_CALL%              | Current round number (with prompt)                                      |
| %RACE_FORMAT%             | Current race format                                                     |
| %LAP_COUNT%               | Current lap number                                                      |
| %LAST_LAP%                | Last lap time for pilot                                                 |
| %AVERAGE_LAP%             | Average lap time for pilot                                              |
| %FASTEST_LAP%             | Fastest lap time                                                        |
| %TIME_BEHIND_CALL%        | Amount of time behind race leader (with prompt)                         |
| %TIME_BEHIND_FINPOS_CALL% | Pilot NAME finished at position X, MM:SS.SSS behind                     |
| %TIME_BEHIND_FINPLACE_CALL% | Pilot NAME finished in X place, MM:SS.SSS behind                      |
| %FASTEST_SPEED%           | Fastest speed for pilot                                                 |
| %CONSECUTIVE%             | Fastest consecutive laps for pilot                                      |
| %TOTAL_TIME%              | Total time since start of race for pilot                                |
| %TOTAL_TIME_LAPS%         | Total time since start of first lap for pilot                           |
| %POSITION%                | Race position for pilot                                                 |
| %POSITION_CALL%           | Race position for pilot (with prompt)                                   |
| %POSITION_PLACE%          | Race position (first, second, etc) for pilot                            |
| %POSITION_PLACE_CALL%     | Race position (first, second, etc) for pilot (with prompt)              |
| %FASTEST_RACE_LAP%        | Pilot/time for fastest lap in race                                      |
| %FASTEST_RACE_LAP_CALL%   | Pilot/time for fastest lap in race (with prompt)                        |
| %FASTEST_RACE_SPEED%      | Pilot/speed for fastest speed in race                                   |
| %FASTEST_RACE_SPEED_CALL% | Pilot/speed for fastest speed in race (with prompt)                     |
| %WINNER%                  | Pilot callsign for winner of race                                       |
| %WINNER_CALL%             | Pilot callsign for winner of race (with prompt)                         |
| %PREVIOUS_WINNER%         | Pilot callsign for winner of previous race                              |
| %PREVIOUS_WINNER_CALL%    | Pilot callsign for winner of previous race (with prompt)                |
| %PILOTS%                  | List of pilot callsigns (read out slower)                               |
| %LINEUP%                  | List of pilot callsigns (read out faster)                               |
| %FREQS%                   | List of pilot callsigns and frequency assignments                       |
| %LEADER%                  | Callsign of pilot currently leading race                                |
| %LEADER_CALL%             | Callsign of pilot currently leading race, in the form "NAME is leading" |
| %SPLIT_TIME%              | Split time for pilot (see [Secondary / Split Timers](../doc/Cluster.md) doc)          |
| %SPLIT_SPEED%             | Split speed for pilot (see [Secondary / Split Timers](../doc/Cluster.md) doc)         |
| %RACE_RESULT%             | Race result status message (race winner or co-op result)                |
| %COOP_RACE_INFO%          | Co-op race mode information (target time or laps)                       |
| %COOP_RACE_LAP_TOTALS%    | Pilot lap counts for race in co-op mode                                 |
| %CURRENT_TIME_AP%         | Current time (12-hour clock)                                            |
| %CURRENT_TIME_24%         | Current time (24-hour clock)                                            |
| %CURRENT_TIME_SECS_AP%    | Current time, with seconds (12-hour clock)                              |
| %CURRENT_TIME_SECS_24%    | Current time, with seconds (24-hour clock)                              |
| %DELAY_#_SECS%            | Delay voice callout by given number of seconds                          |
| %PILOTS_INTERVAL_#_SECS%  | List of callsigns separated by interval seconds (must be only variable) |

#### LED Effects
Choose a visual effect for each timer event. The timer will display this effect when the event occurs, immediately overriding any existing display or effect. Some visual effects are only available on particular timer events. Some visual effects are modified by the event, most notably the color of gate crossing enters/exits. Most effects can be previewed through the LED Control panel.

Some LED effects can be delayed a short time if the timer is busy with time-critical tasks. (Others such as race start are never delayed.) Because of this effect and potentially concurrent crossings, _"Turn Off"_ should usually be avoided for gate exits. Instead, use _"No Change"_ on gate entrance and your desired effect on gate exit.

_This section will not appear if your timer does not have LEDs configured. A notice appears in the startup log._

#### LED Control
This section will override the current LED display. Choose to temporarily shut off the display, display some pre-configured colors, display any custom color, or display a defined effect. You can also use the slider to adjust the brightness of your panel. The ideal setting for FPV cameras is where the lit panel matches the brightness of a white object. This puts the panel output within the dynamic range of what the camera can capture. However, using a low brightness setting distorts color reproduction and smoothness of color transitions.

_This section will not appear if your timer does not have LEDs configured. A notice appears in the startup log._

#### System
Choose the interface language, and change parameters that affect the appearance of the timer such as its name and color scheme. You can also shut down the server from here.

#### Status
Provides information about sensors and the timer cluster (secondary/split and mirror timers). A _reconnect_ button appears here if cluster timer communications fail and RotorHazard cannot automatically recover.


### Run

This page allows you to control the timer and run races.

Select the Heat for the race which is to be run next.

Start the race when ready. (Hotkey: <kbd>z</kbd>) The timer will do a quick communication to the server to  compensate for client/server response time, then begin the staging procedure defined by the current race format.

Tuning parameters can be adjusted here by clicking on/touching any of the graphs for each node. See [doc/Tuning Parameters.md](Tuning%20Parameters.md) for a detailed description and tuning guide.

During the race, there is an "×" next to each counted lap. This will discard that lap pass, so its time is moved to the next lap. Use this to remove errant extra passes, or clean up pilots flying close to the start gate after their race finished.

Pressing the "+ Lap" button will manually trigger a lap pass for that node.

When a race is over, use the "Stop Race" button (Hotkey: <kbd>x</kbd>) to discontinue counting laps. You need to do this  even if the timer reaches zero in a "Count Down" format—a popular race format allows pilots to finish the lap they are on when time expires. For best results, clear the timing gate and allow all valid crossings to end before stopping the race.

Once a race has concluded, you must choose "Save Laps" or "Discard Laps" before starting another race. "Save Laps" (Hotkey: <kbd>c</kbd>) will store race results to the database and display them on the "Results" page. "Discard Laps" (Hotkey: <kbd>v</kbd>) will discard the race results. Saving laps will automatically advance the heat selection to the next heat with the same class as the saved race.

(The spacebar can also be used as a hotkey for the Start, Stop and Save functions.)

The Race Management panel provides quick access to change the current Race Format, Profile, Minimum Lap Time, or Team/Co-op Racing Mode. _Audio Control_ and _LED Control_ are the same as the Settings page. The History Export dumps a CSV file to be downloaded of the recorded RSSI values in the most recently completed race. "Time Until Race Start" will schedule a race to be run at a future time. Operators may use this to set a hard limit on the amount of time allowed for pilots to prepare, or to start the timer and then participate in the race themselves.

The Callout panel may be used to configure voice callouts, which can be triggered by clicking on the "play" button or hitting the associated hot-key sequence.  (For instance, hitting Ctl+Alt+1 will trigger the first voice callout.)  Many of the variables listed under "Event Actions" may be used on these callouts.

### Marshal

Adjust results of saved races.

Select the round, heat, and pilot to adjust. Enter and Exit points are automatically loaded from the saved race data. Adjust the Enter and Exit points to recalibrate the race after the fact. "Load from Node" to copy current live calibration data over the active values. "Save to Node" to copy the active values over the current live values. "Recalculate Race" to use the active Enter/Exit values as calibration points for a "re-run" of the race. This will erase current laps and replace them with the recalculated information. Manually entered laps are preserved.

Add laps by entering the crossing time in seconds from the beginning of the race, then pressing the "Add Lap" button.

Delete laps with the "×" button on the unwanted lap. Deleted laps are removed from calculations but remain present in the data for later reference. "Discard Laps" to permanently remove the data from the database.

You may click on/touch the graph to set enter/exit points, activate recalculation, and highlight specific laps. Clicking on laps in the list also adds a highlight on the graph. Press <kbd>delete</kbd> or <kbd>x</kbd> to delete a highlighted lap. Active laps are displayed in green, and deleted laps change to red. The width of the lap indicator shows the enter/exit points, and the yellow highlight draws a line at the exact lap time within that window.

"Commit changes" when you are finished adjusting the race data to save it to the database and update the race results.

<br/>

-----------------------------

See Also:<br/>
[doc/Tuning Parameters.md](Tuning%20Parameters.md)<br/>
[doc/Software Setup.md](Software%20Setup.md)<br/>
[doc/Hardware Setup.md](Hardware%20Setup.md)<br/>
[Build Resources (PCB, etc) &#10132;&#xFE0E;](https://github.com/RotorHazard/RotorHazard/tree/main/resources/README.md)
