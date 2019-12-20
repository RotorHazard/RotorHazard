# Calibration and Sensor Tuning Parameters

The RotorHazard timing system allows you to calibrate each node individually, so that you can compensate for the behavior and hardware differences across your system and environment.

Each node keeps track of the signal strength (RSSI) on a provided frequency, and uses the relative strength to determine its position relative to the start/finish gate. A node can be *crossing* or *clear*. If a node is *clear*, the system believes the quad is not near the start/finish gate. If it is *crossing*, the system believes the quad is passing by the start/finish gate and a lap pass will be recorded once the *crossing* is finished.

## Parameters
Parameters that affect the *crossing* status are *EnterAt* and *ExitAt*.

### EnterAt
The system will consider a quad to be *crossing* once the RSSI raises to or above this level.

### ExitAt
The system will consider a quad to have finished *crossing* once the RSSI value drops below this level.

## Tuning
Before during any of the other tuning procedures:

1. Power up the timer and keep it running for a few minutes to allow its modules to warm up. (The RSSI values tend to increase by a few points as the timer heats up.)

2. Power up a quad and bring it very close to the timer for a few seconds. This will allow the timer to capture the peak-RSSI value for that node. This should be done for any node/channel that is being tuned.

The *Capture* buttons may be used to store the current RSSI reading as the EnterAt or ExitAt value for that node. The values may also be entered and adjusted manually.

### Set the *EnterAt* value:
* High enough that it is only reached when the quad is near the start/finish gate.
* Not so high that a quad cannot reach it as it approaches the start/finish gate.
* Higher than *ExitAt*.

A good starting point is to capture the EnterAt value with a quad about 5–10 feet away from the timer. If gate crossings are being missed then lower this value. If gate crossing are triggered when they shouldn't be then increase this value.

### Set the *ExitAt* value:
* Low enough that RSSI noise during a gate pass does not trigger multiple *crossings*.
* High enough that that the quad will always drop below the value at some point on the course. (The lowest value recorded since the last pass is displayed as the *Nadir*.)
* Lower than *EnterAt*.

A good starting point is to capture the ExitAt value with a quad about 20–30 feet away from the timer. If a pass by the timer is resulting in multiple crossings, try lowering this value. If the 'Crossing' indicator is stuck on, try increasing this value.

### Sample RSSI Graph:

![Sample RSSI Graph](img/Sample%20RSSI%20Graph.svg)

## Alternate Tuning Method

You can use Marshaling to tune values visually. Run a race with a pilot on each channel, then save it. Open the Marshal page and view the race data, adjusting Enter and Exit points until the number of laps is correct. Save the Enter/Exit points to each node to use as calibration for future races.

## Notes
* Try to keep *EnterAt* and *ExitAt* further apart than the size of noise spikes/dips.
* Dropping below the *EnterAt* value during a pass is fine, as long as the level stays above *ExitAt* until the pass is complete.
* Spiking above *ExitAt* after a pass is fine, as long as the spike doesn't reach *EnterAt*.
* A very low *ExitAt* value (but above the *Nadir*) will still provide accurate timing, but the system will wait longer before announcing laps.
* The *Minimum Lap Time* setting can be used to prevent extra passes, but might mask *crossings* that are triggered too early. It is recommended to leave the behavior at *Highlight* rather than *Discard*.

## Troubleshooting
Laps registering on other parts of a course:
* Raise *EnterAt* until *crossings* only begin near the start/finish gate. Use the *Marshal* page after saving a race to determine the best values.

Many laps registering at once:
* Raise *EnterAt*, if possible
* Lower *ExitAt*,

Laps taking a long time to register:
* Raise *ExitAt*

Node is never *crossing*:
* Lower *EnterAt*

Node is never *clear*:
* Raise *ExitAt*

## Retroactive Pass Recording
If you notice a pass was not recorded, you may use the "Catch Missed Pass" button. The timer will review recent RSSI history for the node and find the most likely occurrence of a missed pass, recording it as a lap. The node's EnterAt value is then adjusted so that similar passes to the one marked as "missed" will be counted in the future. If the adjustment would make the node unstable, a warning is issued instead.

If you notice a node crossing does not complete within a reasonable time, you may use the "Force End Crossing" button. The timer will review recent RSSI history for the node and find a low point where the crossing could be safely ended. The node's ExitAt value is then adjusted so that passes will end at this point in the future. If the adjustment would make the node unstable, a warning is issued instead.

The window of time both of these functions use is based on the current "minimum lap" setting.
