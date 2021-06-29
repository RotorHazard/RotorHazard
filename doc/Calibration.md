# Node calibration

Three calibration modes are supported.

## Auto-calibration (supervised ML)

Adjusts the *enter* and *exit* values based on saved laps
(or changes committed using marshalling).

## AI calibration (unsupervised ML with gradient descent)

Adjusts the *enter* and *exit* values at the end of each race based on RSSI data only.
This is a "no-fuss" approach that works best with well performing receivers.

## Manual calibration

Manually adjust the *enter* and *exit* values.
