# Delta 5 Race Timer User Guide

### Hardware and Software Setup
Follow the instructions here if not done already: [/doc/Hardware and Software Setup Instructions.md](Hardware%20and%20Software%20Setup%20Instructions.md)

### Connect to the Server
Find the ip address of the raspberry pi by opening the 'Clients' list on your routers admin page.

Open a browser and type in the ip address of the timing system on your network using port 5000 or as configured in 'server.py'.
```
XXX.XXX.XXX.XXX:5000/
```

Pages reserved for the race director are password protected with the default user 'admin' and password 'delta5'.

### System Settings and Configuration ('Settings' page)

Start by resetting the database at the start of each race event. You have the option of a complete reset 'Reset Database' or if mostly the same pilots are racing 'Reset Keep Pilots'.

Frequencies are configured under the Nodes heading. Defaults are IMD for up to 6 nodes or Raceband when 7 or 8 nodes are detected. Use the dropdowns to change frequencies as needed.

Click 'Add Pilot' until you have an entry for each pilot racing and then update the pilot callsigns and names.

Click 'Add Heat' until there are enough for all the pilots racing. Assign each pilot to a heat using the drop down buttons. The '-' pilot can be used for blank positions.

If you are noticing any missed or multiple laps when passing the gate, the sensor tuning values can be adjusted from defaults with a detailed description found here [/doc/Tuning Parameters.md](Tuning%20Parameters.md)

The following voices are available for selection for lap time call outs (these are broswer dependent, but has been tested in Chrome):
```
David - English (United States) en-US
Zira - English (United States) en-US
US English en-US
UK English Female en-GB
UK English Male en-GB
Deutsch de-DE
español es-ES
español de Estados Unidos es-US
français fr-FR
हिन्दी hi-IN
Bahasa Indonesia id-ID
italiano it-IT
日本語 ja-JP
한국의 ko-KR
Nederlands nl-NL
polski pl-PL
português do Brasil pt-BR
русский ru-RU
國語（臺灣） zh-TW
```

### Running Races ('Race' page)

The race director will spend most of their time on this page running races.

Start by selecting the 'Heat' button to set which heat will be racing.

Click 'Start Race' for a count up timer starting from zero with no defined end. This is used for heads up racing, first to finish X laps. The race director clicks the 'Stop Race' button after all pilots have completed their laps.

Alternatively click the 'Start Race 2min' for a count down timer from two minutes. This is used for most laps racing, each pilot has two minutes to complete as many laps as possible. After the last buzzer and all pilots have completed their last lap, click the 'Stop Race' button.

For each node in a row under the pilot callsigns will be the RSSI values, Current RSSI / Trigger / Peak. This gives the race director immediate sensor feedback for any adjustments that might need to be made.

During a race there will be a 'X' button next to each lap. This will discard that lap and move it's time into the next lap if it's not the last lap. It's generally perferable to tune the system to pick up more laps instead of missing laps and this is how the extras are deleted. At the end of the race you may have pilots flying by the start gate when they go to land, this is also how you remove those laps which might get picked up.

After each race, click 'Save Laps' to store the results of a good race to the database, or 'Clear Laps' for a false start or as needed to discard the current laps.

### Saved Races ('Rounds' page)

This is a public page, previous race results are displayed on this page sorted by heats and rounds.

### Pilots and Heats ('Heats' page)

Also a public page, shows a summary of pilots and their heats with channel assignment.
