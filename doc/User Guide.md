# RotorHazard Race Timer User Guide

## Initial Setup

### Hardware and Software Setup
Follow the instructions here if not done already:<br>
[Hardware Setup](Hardware%20Setup.md)<br>
[Software Setup](Software%20Setup.md)<br>
[RF shielding](Shielding%20and%20Course%20Position.md)

### Set up Config File
In the "src/server" directory, find *config-dist.json* and copy it to *config.json*. Edit this file and modify the ADMIN_USERNAME and ADMIN_PASSWORD values. This items in this file must in valid JSON format. A linter utility like [JSONLint](https://jsonlint.com/) can be used to check for syntax errors.

ADMIN_USERNAME and ADMIN_PASSWORD are the login credentials you will need to access the pages reserved for the race director (i.e., the *Settings* and *Run* pages).

### Connect to the Server
A computer, phone or tablet may be used to interact with the race timer by launching a web browser and entering the IP address of the Raspberry Pi. The Raspberry Pi may be connected using an ethernet cable, or to an available WiFi network. If the IP address of the Pi is not known, it may be viewed using the terminal command "ifconfig", and it can configured to a static value on the Pi desktop via the "Network Preferences." If the Pi is connected to a WiFi network, its IP address may be found in the 'Clients' list on the admin page for the network's router.

In the web browser, type in the IP address of for the race timer and the port value you set in the config file (or leave off the :port if set to 80).

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


### Settings

This page allows changing the timer's optional settings and event setup.

#### Frequency Setup
Choose a preset or manually select frequencies for each node. Arbitrary frequency selection is possible, as is disabling a node. The IMD score for currently selected frequencies is calculated and displayed at the bottom of the panel.

Profiles contain frequencies and node tuning values. Changing this list immediately activates the selected profile, and changing current frequencies and node tuning immediately saves to the profile.

#### Sensor Tuning
See [doc/Tuning Parameters.md](Tuning%20Parameters.md) for a detailed description and tuning guide.

#### Event and Classes
Event information is displayed on the home page when users first connect to the system.

Classes are not required for events; there's no need to create a class unless you will have two or more in the event. Classes can be used to have separate generated statistics for groups of heats. For example, Open and Spec class, or Beginner/Pro classes.

#### Heats
Add heats until there are enough for all pilots racing. Optional heat names can be added if desired. Heat slots may be set to *None* if no pilot is assigned there.

If you are using classes, assign each heat to a class. Be sure to add enough heats for each pilot in each class; heats assigned to one class are not available in another.

As you run races, heats will become locked and cannot be modified. This protects saved race data from becoming invalid. To modify heats again, open the *Database* panel and clear races.

#### Pilots
Add an entry for each pilot that will race. The system will announce pilots based on their callsign. A phonetic spelling for a callsign may be used to influence the voice callouts; it is not required.

#### Audio Control
All audio controls are local to the browser and device where you set them, including the list of available languages, volumes, and which announcements or indicators are in use.

Voice select chooses the text-to-speech engine. Available selections are provided by the web browser and operating system.

Announcements allow the user to choose to hear each pilot's callsign, lap number, and/or lap time as they cross. The "Race Timer" announcement will perioically call out how much time has elapsed or is remaining, depending on the timer mode in the race format. "Team Lap Total" is used only when "Team Racing Mode" is enabled.

Voice volume, rate, and pitch control all text-to-speech announcements. "Tone Volume" controls race start and end signals.

Indicator beeps are very short tones that give feedback on how the timer is working, and are most useful when trying to tune it. Each node is identified with a unique audio pitch. "Crossing Entered" will beep once when a pass begins, and "Crossing Exited" will beep twice rapidly when a pass is completed. "Manual Lap Button" will beep once if the "Manual" button is used to force a simulated pass.

#### Race Format
Race formats define how a race is conducted. Choose an active race format. Settings that you adjust here will be saved to the currently active format.

The race timer can count up or down as selected by _Race Timer Mode_. Use "No Time Limit" for a "first to X laps" style with a timer that counts upward from zero. Use "Fixed Time" for a timer which counts down to zero after the race starts. _Timer Duration_ is used in "Fixed Time" mode to determine race length.

Each race begins with a staging sequence. Race staging can be done with a fixed or variable number of staging seconds and with or without staging tones. Set the _Minimum Start Delay_ and _Maximum Start Delay_ to the values (in seconds) that are desired for race staging. If these values are different, the timer will choose a value at random for the amount of staging time. Random staging times are useful to prevent false starts. The timer will display "Ready" during staging, obscuring the race start time. For a fixed staging time, set the "Minimum" and "Maximum" to the same value. The staging timer will openly display the number of seconds until the race begins. 

_A small amount of time is needed to ensure the timer has synchronized with all hardware, so there is a short staging period even with a staging time of zero._

A number of tones can be generated during the staging sequence, as set by _Staging Tones_. For "Each Second", the timer will sound a tone continuously during staging. With "One", the timer will sound a tone immediately when staging begins. With "None", no audible warning is provided. Regardless of the _Staging Tones_ setting, the "Race Start" tone is still played when staging completes and the race begins.

_Win Condition_ determines how the timer calls out the winner of the race, the information presented in the OSD and streaming display, and sort method for leaderboards. Leaderboard sorting affects the results page and heat generator.
* __Most Laps in Fastest Time__: Pilots are judged by the number of laps completed and how long it took to complete them. If there is a tie for the number of laps completed, the pilot who completed those laps in a shorter amount of time will be ranked higher.
* __Most Laps Only__: Scored only by the completed lap count. Pilots with the same lap count are tied. Use with "Fixed Time" mode for a race style before timing was reliable, or with "No Time Limit" mode to judge the greatest distance instead of shortest time.
* __Most Laps Only with Overtime__: Similar to _Most Laps in Fastest Time_, but with a "sudden death" component. When the timer expires (or the race is stopped early), if a pilot has more laps than all the others then that pilot is the winner. If there is a tie for lap count when the timer expires, the first of the tied pilots across the line is the winner.
* __First to X Laps__: The race continues until one pilot reaches the desired lap count. In this mode, the _Number of Laps to Win_ parameter is used. Typically used with the _No Time Limit_ race mode.
* __Fastest Lap__: Ignores the race progress and considers only each pilot's single fastest lap.
* __Fastest 3 Consecutive Laps__: Considers all laps a pilot has completed and uses the three consecutive laps with the fastest combined time.
* __None__: Does not declare a winner under any circumstance. Heats generated from a class with this condition will be assigned randomly.

_Team Racing Mode_ activates alternate scoring for additional race formats. Win conditions in team racing mode differ somewhat:
* __Most Laps in Fastest Time__: Teams are judged on combined lap count of all members and how long it took to complete those laps.
* __Most Laps Only__: Teams are judged on total combined lap count of all members.
* __Most Laps Only with Overtime__: Teams are judged on total combined lap count of all members. If tied when time expires, the first team (of those tied) to add a lap becomes the winner.
* __First to X Laps__: The first team to complete the desired combined lap count is the winner.
* __Fastest Lap__: After all team members have contributed one lap, teams are judged by the average of pilots' fastest lap time.
* __Fastest 3 Consecutive Laps__: After all team members have contributed 3 laps, teams are judged by the average of pilots' fastest "three consecutive laps" time.

With _Fastest Lap_ and _Fastest 3 Consecutive Laps_, teams with differing numbers of pilots can compete together fairly.

_Minimum lap Time_ highlights or discards passes that would have registered laps less than the specified duration. Use the "discard" behavior with caution, as this will eliminate data that may have been valid. _Minimum Lap Time_ is not stored with the race format.

#### LED Effects
Choose a visual effect for each timer event. The timer will display this effect when the event occurs, immediately overriding any existing display or effect. Some visual effects are only available on particular timer events. Some visual effects are modified by the event, most notably the color of gate crossing enters/exits. Most effects can be previewed through the LED Control panel.

Some LED effects can be delayed a short time if the timer is busy with time-critical tasks. (Others such as race start are never delayed.) Because of this effect and potentially concurrent crossings, _"Turn Off"_ should usually be avoided for gate exits. Instead, use _"No Change"_ on gate entrance and your desired effect on gate exit.

_This section will not appear if your timer does not have LEDs configured. A notice appears in the startup log._

#### LED Control
This section will override the current LED display. Choose to temporarily shut off the display, display some pre-configured colors, display any custom color, or display a defined effect. You can also use the slider to adjust the brightness of your panel. The ideal setting for FPV cameras is where the lit panel matches the brightness of a white object. This puts the panel output within the dynamic range of what the camera can capture. However, using a low brightness setting distorts color reproduction and smoothness of color transitions.

_This section will not appear if your timer does not have LEDs configured. A notice appears in the startup log._

#### Database
Choose to backup the current database (save to a file on the pi and prompt to download it) or clear data. You may clear races, classes, heats, and pilots.

#### System
Choose the interface language, and change parameters that affect the appearance of the timer such as its name and color scheme. You can also shut down the server from here.


### Run

This page allows you to control the timer and run races.

Select the Heat for the race which is to be run next.

Start the race when ready. (Hotkey: <kbd>z</kbd>) The timer will do a quick communication to the server to  compensate for client/server response time, then begin the staging procedure defined by the current race format.

Tuning parameters can be adjusted here via the "⚠" button. See [doc/Tuning Parameters.md](Tuning%20Parameters.md) for a detailed description and tuning guide.

During the race, there is an "×" next to each counted lap. This will discard that lap pass, so its time is moved to the next lap. Use this to remove errant extra passes, or clean up pilots flying close to the start gate after their race finished.

Pressing the "+ Lap" button will manually trigger a lap pass for that node.

When a race is over, use the "Stop Race" button (Hotkey: <kbd>x</kbd>) to discontinue counting laps. You need to do this  even if the timer reaches zero in a "Count Down" format—a popular race format allows pilots to finish the lap they are on when time expires. For best results, clear the timing gate and allow all valid crossings to end before stopping the race.

Once a race has concluded, you must choose "Save Laps" or "Discard Laps" before starting another race. "Save Laps" (Hotkey: <kbd>c</kbd>) will store race results to the database and display them on the "Results" page. "Discard Laps" (Hotkey: <kbd>v</kbd>) will discard the race results. Saving laps will automatically advance the heat selection to the next heat with the same class as the saved race.

The Race Management panel provides quick access to change the current Race Format, Profile, Minimum Lap Time, or Team Racing Mode. _Audio Control_ and _LED Control_ are the same as the Settings page. The History Export dumps a CSV file to be downloaded of the recorded RSSI values in the most recently completed race. "Time Until Race Start" will schedule a race to be run at a future time. Operators may use this to set a hard limit on the amount of time allowed for pilots to prepare, or to start the timer and then participate in the race themselves.

### Marshal

Adjust results of saved races.

Select the round, heat, and pilot to adjust. Enter and Exit points are automatically loaded from the saved race data. Adjust the Enter and Exit points to recalibrate the race after the fact. "Load from Node" to copy current live calibration data over the active values. "Save to Node" to copy the active values over the current live values. "Recalculate Race" to use the active Enter/Exit values as calibration points for a "re-run" of the race. This will erase current laps and replace them with the recalculated information. Manually entered laps are preserved.

Add laps by entering the crossing time in seconds from the beginning of the race, then pressing the "Add Lap" button.

Delete laps with the "×" button on the unwanted lap. Deleted laps are removed from calculations but remain present in the data for later reference. "Discard Laps" to permanently remove the data from the database.

You may click on/touch the graph to set enter/exit points, activate recalculation, and highlight specific laps. Clicking on laps in the list also adds a highlight on the graph. Press <kbd>delete</kbd> or <kbd>x</kbd> to delete a highlighted lap. Active laps are displayed in green, and deleted laps change to red. The width of the lap indicator shows the enter/exit points, and the yellow highlight draws a line at the exact lap time within that window.

"Commit changes" when you are finished adjusting the race data to save it to the database and update the race results.
