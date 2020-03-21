# Calibration and Sensor Tuning Parameters

_If you are having trouble calibrating your timer, be sure you have constructed and placed [RF shielding](Shielding%20and%20Course%20Position.md) correctly._

Each node keeps track of the signal strength (RSSI) on a selected frequency and uses this relative strength to determine whether a transmitter is near the timing gate. The RotorHazard timing system allows you to calibrate each node individually so that you can compensate for the behavior and hardware differences across your system and environment.

A node can be *Crossing* or *Clear*. If a node is *Clear*, the system believes a transmitter is not near the timing gate because the RSSI is low. If it is *Crossing*, the system believes a transmitter is passing by the timing gate because the RSSI is high. A lap pass will be recorded once the *Crossing* is finished and the system returns to *Clear*.

![Tuning Graph](img/Tuning%20Graph-06.svg)<br />
_RSSI during a race appears similar to this graph with many visible peaks and valleys. As the transmitter nears the timing gate, the signal rises._

## Parameters
Two parameters that affect the *Crossing* status: *EnterAt* and *ExitAt*.

### EnterAt
The system will switch to *Crossing* when RSSI raises to or above this level. It is indicated by a red line.

### ExitAt
The system will switch to *Clear* once the RSSI value drops below this level. It is indicated by an orange line.

In between *EnterAt* and *ExitAt*, the system will remain *Crossing* or *Clear* depending on its previous state.

![Sample RSSI Graph](img/Sample%20RSSI%20Graph.svg)

### Calibration Mode

*Manual* calibration mode will always use the *EnterAt* and *ExitAt* values provided by the user.

*Adaptive* calibration mode uses the user-defined points unless there are saved races. When saved races exist, changing heats will initiate a search of previous race data for the best calibration values to use in the upcoming race. These values are copied and replace the current *EnterAt* and *ExitAt* values for all nodes. This mode improves calibration as more races are saved if the race director confirms the incoming lap counts or recalculates them through the *Marshal* page.

## Tuning
Before tuning, power up the timer and keep it running for a few minutes to allow the receiver modules to warm up. The RSSI values tend to increase by a few points as the timer heats up.

You can use the *Marshal* page to tune values visually. Collect data by running a race with a pilot on each channel, then save it. Open the *Marshal* page and view the race data, adjusting Enter and Exit points until the number of laps is correct. Save the Enter/Exit points to each node to use as calibration for future races.

### Set the *EnterAt* value
![Tuning Graph](img/Tuning%20Graph-10.svg)

* Below the peak of all gate crossings
* Above any peak when the transmitter is not near the gate
* Higher than *ExitAt*

### Set the *ExitAt* value
![Tuning Graph](img/Tuning%20Graph-11.svg)

* Below any valleys that occur during a gate crossing
* Above the lowest value seen during any lap
* Lower than *EnterAt*

ExitAt values closer to EnterAt allow the timer to announce and display laps sooner, but can cause multiple laps to be recorded.

### Tuning Example
![Tuning Graph](img/Tuning%20Graph-01.svg)<br />
_Two laps are recorded. The signal rises above *EnterAt* and then falls below *ExitAt* twice, once at each peak. Within these two crossing windows, the timer finds the strongest signal after noise filtering to use as the recorded lap time._

### Alternate Tuning Method

The *Capture* buttons may be used to store the current RSSI reading as the *EnterAt* or *ExitAt* value for each node. The values may also be entered and adjusted manually.

Power up a quad on the correct channel and bring it very close to the timer for a few seconds. This will allow the timer to capture the peak RSSI value for that node. This should be done for each node/channel that is being tuned. The peak value will be displayed.

#### EnterAt
A good starting point for *EnterAt* is to capture value with a quad about 1.5–3m (5–10 ft) away from the timer.

#### ExitAt
A good starting point for *ExitAt* is to capture the value with a quad about 6–9m (20–30 ft) away from the timer.

## Notes
* A low *ExitAt* value can still provide accurate timing, but the system will wait longer before announcing laps. A delay in announcing does not affect the accuracy of the timer.
* The *Minimum Lap Time* setting can be used to prevent extra passes, but might mask crossings that are triggered too early. It is recommended to leave the behavior at *Highlight* rather than *Discard*.
* If you experience timing issues during a race and the RSSI graphs are responding to transmitter location, do not stop the race. Save the race after it completes and visit the *Marshal* page. All RSSI history is saved and the race can be accurately recalculated with updated tuning values.

## Troubleshooting

### Missing Laps (System usually *Clear*)
![Tuning Graph](img/Tuning%20Graph-04.svg)<br />
_Laps are not recorded if RSSI does not reach EnterAt._
* Lower *EnterAt*

### Missing Laps (System usually *Crossing*)
![Tuning Graph](img/Tuning%20Graph-05.svg)<br />
_Laps are merged together if *ExitAt* is too high because the first lap crossing never completes._
* Raise *ExitAt*

### Laps register on other parts of a course
![Tuning Graph](img/Tuning%20Graph-03.svg)<br />
_Extra crossings occur when *EnterAt* is too low._
* Raise *EnterAt* until *crossings* only begin near the timing gate. (Use the *Marshal* page after saving a race to determine and save the best values.)

### Many laps register at once
![Tuning Graph](img/Tuning%20Graph-02.svg)<br />
_Too many laps occur when *ExitAt* is too close to *EnterAt* because laps exit too quickly._
* Raise *EnterAt*, if possible
* Lower *ExitAt*

The *Minimum Lap Time* setting always keeps the first crossing and disards subsequent laps that occur too soon. In this instance, this setting would discard the correct first crossing and keep the incorrect second crossing. It is recommended to leave the *Minimum Lap Time* behavior at *Highlight* rather than *Discard* so that a race organizer can manually review each case.

### Laps take a long time to register
![Tuning Graph](img/Tuning%20Graph-09.svg)<br />
_Lap recording takes a long time to complete if *ExiAt* is low. This does not affect the accuracy of the recorded time._
* Raise *ExitAt*

### Node is never *crossing*
![Tuning Graph](img/Tuning%20Graph-07.svg)<br />
_Laps will not register if RSSI never reaches *EnterAt*._
* Lower *EnterAt*

### Node is never *clear*
![Tuning Graph](img/Tuning%20Graph-08.svg)<br />
_Laps will not complete if RSSI never drops below *ExitAt*._
* Raise *ExitAt*
