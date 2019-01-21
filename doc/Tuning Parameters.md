# Calibration and Sensor Tuning Parameters

The RotorHazard timing system allows you to calibrate each node individually, so that you can compensate for the behavior and hardware differences across your system and environment.

Each node keeps trask of the signal strength (RSSI) on a provided frequency, and uses the relative strength to determine its position relative to the start line. A node can be *crossing* or *clear*. If a node is *clear*, the system believes no quad is near the start line. If it is *crossing*, the system believes a quad is passing by the start line and a lap pass will be recorded once the *crossing* is finished.

## Parameters
Paramaters that affect *crossing* status are EnterAt, ExitAt, and Smoothing.

### EnterAt
The system will consider a quad to be *crossing* once the RSSI raises above this level.

### ExitAt
The system will consider a quad to have finished *crossing* once the RSSI value drops below this level.

### RSSI Smoothing
Adjusts the filtering on the RSSI value, to reduce noise. Less noise creates cleaner data that triggers more easily, but delays the response time of a node. Too much smoothing could prevent high-speed passes from being recorded. Apply higher smoothing indoors.

## Tuning
You may capture a value by powering up a quad and pressing the *Capture* button. This will store the current RSSI into this value. Be sure to have passed the quad very near the timer before you use the *Capture* buttons, so that the system understands what the peak RSSI will look like.

### Set the *EnterAt* value:
* High enough that it is not reached at any other position on the course.
* Not so high that a quad cannot reach it as it approaches the start line.
* Higher than *ExitAt*.
A good starting point is to capture the value with a quad about 5–10 feet away from the timer.

### Set the *ExitAt* value:
* Low enough that RSSI noise during a gate pass does not trigger multiple *crossings*.
* High enough that that the quad will always drop below the value at some point on the course. (The lowest value reorded since that lasst pass is displayed as the *Nadir*.)
* Lower than *enterAt*.
A good starting point is to capture the value with a quad about 20–30 feet away from the timer.

If crossings are still erratic, increase *RSSI Smoothing* to reduce noise.

![Sample RSSI Graph](img/Sample%20RSSI%20Graph.svg)

## Notes
* Try to keep *EnterAt* and *ExitAt* further apart than the size of noise spikes/dips.
* Dropping below the *EnterAt* value during a pass is fine, as long as the level stays above *ExitAt*.
* Spiking above *ExitAt* after a pass is fine, as long as the spike doesn't reach *EnterAt*.
* Increase *RSSI Smoothing* to reduce the amount of noise.
* A very low *ExitAt* value (but above the *Nadir*) will still work, but the system will wait until it is reached before announcing laps.
* Actual timing uses raw RSSI values collected within the *crossing* window, irrespective of *Smoothing*. Heavy smoothing does not affect lap times, but could prevent high-speed passes from registering as *crossing*.
* The *Minimum Lap Time* setting can be used to prevent extra passes, but might mask *crossings* that are triggered too early.

## Troubleshooting
Laps registering on other parts of a course: 
* Raise *EnterAt* until *crossings* only begin near the start line

Many laps registering at once:
* Raise *EnterAt*, if possible
* Lower *ExitAt*, 
* Increase *RSSI Smoothing*

Laps taking a long time to register:
* Raise *ExitAt*

Node is never *crossing*:
* Lower *EnterAt*

Node is never *clear*:
* Raise *ExitAt*

Missing high-speed passes:
* Decrease *RSSI Smoothing*
