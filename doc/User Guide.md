# RotorHazard Race Timer User Guide

## Initial Setup

### Hardware and Software Setup
Follow the instructions here if not done already:  
[doc/Hardware Setup.md](Hardware%20Setup.md)  
[doc/Software Setup.md](Software%20Setup.md)

### Set up Config File
In the "src/server" directory, find *config-dist.json* and copy it to *config.json*. Edit this file and modify the HTTP_PORT, SECRET_KEY, ADMIN_USERNAME, and ADMIN_PASSWORD values. Make sure you keep this config file as valid JSON. A linter utility like [JSONLint](https://jsonlint.com/) can be used to check for syntax errors.

HTTP_PORT is the port value the server will run on. By default, HTTP uses port 80. Other values will require that the port be included as part of the URL entered into client browsers. If other web services are running on the Pi, port 80 may already be in use and the server will fail to start. Port 5000 should be available. (Note that if port 80 is used, the server will need to be run using the *sudo* command.)

SECRET_KEY should be modified to any random value.

ADMIN_USERNAME and ADMIN_PASSWORD are the login credentials you will use to make changes to settings.


### Connect to the Server
A computer, phone or tablet may be used to interact with the race timer by launching a web browser and entering the IP address of the Raspberry Pi. The Raspberry Pi may be connected using an ethernet cable, or to an available WiFi network. If the IP address of the Pi is not known, it may be viewed using the terminal command "ifconfig", and it can configured to a static value on the Pi desktop via the "Network Preferences." If the Pi is connected to a WiFi network, its IP address may be found in the 'Clients' list on the admin page for the network's router.

In the web browser, type in the IP address of for the race timer and the port value you set in the config file (if not 80).
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

#### Profiles
Profiles contain settings for various circumstances or environments, such as outdoor and indoor areas. Settings saved into the profile are frequencies, node tuning values, and RSSI smoothing. Choose an active profile. Settings that you adjust will be saved to the currently active profile.

#### Frequency Setup
Choose a preset or manually select frequencies for each node. Arbitrary frequency selection is possible, as is disabling a node. The IMD score for currently selected frequencies is calculated and displayed at the bottom of the panel.

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
Race formats collect settings that define how a race is conducted. Choose an active race format. Settings that you adjust here will be saved to the currently active format.

Timer mode can count up, or count down. Use "Count Up" for a heads-up, "first to X laps" style. Use "Count Down" for a fixed-time format. Timer duration is only used in "Count Down" mode.

Staging Timer Mode affects whether the time display will be visible before a race. "Show Countdown" will show the time until the race start signal; "Hide Countdown" will display "Ready" until the race begins.

Minimum and Maximum Start Delay adjust how many second the staging (pre-race) timer lasts. Set these to the same number for a fixed countodwn time, or to different numbers for a random time within this range.

Minimum lap time and team racing mode are not stored with the race format.

Minimum lap time automatically discards passes that would have registered laps less than the specified duration. Use with caution, as this will discard data that may have been valid.

#### LED Control
This section will override the current LED display.

#### Database
Choose to backup the current database (save to a file on the pi and prompt to download it) or clear data. You may clear races, classes, heats, and pilots.

#### System
Choose the interface language, and change parameters that affect the appearance of the timer such as its name and color scheme. You can also shut down the server from here.


### Run

Select the Heat for the race which is to be run next.

Start the race when ready. The timer will do a quick communication to the server to  compensate for client/server response time, then begin the staging procedure defined by the current race format.

Tuning parameters can be adjusted here via the "⚠" button. See [doc/Tuning Parameters.md](Tuning%20Parameters.md) for a detailed description and tuning guide.

During the race, there is an "×" next to each counted lap. This will discard that lap pass, so its time is moved to the next lap. Use this to remove errant extra passes, or clean up pilots flying close to the start gate after their race finished.

A "+ Lap" button is provided to force lap pass for that node to be immediately recorded.

You must use the "Stop Race" button to discontinue counting laps. This is true even if the timer reaches zero in a "Count Down" format—a popular race format allows pilots to finish the lap they are on when time expires.

Once a race has concluded, you must choose "Save Laps" or "Clear Laps" before starting another race. "Save Laps" will store race results to the database and display them on the "Results" page. "Clear Laps" will discard the race results.

The Race Management panel provides quick access to change the current Race Format, Profile, Minimum Lap Time, or Team Racing Mode. Audio Control and LED Contral are the same as the Settings page. The History Export dumps a CSV file to be downloaded of the recorded RSSI values in the most recently completed race.
