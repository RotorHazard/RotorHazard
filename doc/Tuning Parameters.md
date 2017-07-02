# Tuning parameters

There are a few parameters that can be used to tune the behavior of the delta5 nodes.  This document will attempt to explain them.

## Auto Calibration

The delta5 will auto-calibrate the trigger value for the nodes during the first pass of the timing gate.  In order for auto-calibration to work, the system has to make a guess about when a quad passes the gate the first time. In theory, the RSSI will go up as you approach the timing gate and then fall as you travel away from it. In practice, there is a lot of noise and the value oscillates quite a bit.

Auto-calibration works best with the launch pads and start gate positioned in the middle of a straight away.  You want a clean rise and fall of the RSSI value at the start and for each lap.

**Calibration Threshold** - Helps to add a buffer around the fluctuating RSSI value during the first pass.  Before a peak in the RSSI value is considered to be a gate pass, it must first fall below *Peak RSSI - Calibration Offset*. Set this value higher if you are getting lower than expected trigger values because the fist pass has been triggered before actually crossing the gate.  If you are not getting a pass record for the fist pass (and likely ever), lower this value; The quad has not gotten far enough away from the gate for the RSSI to fall below *Peak RSSI - Calibration Offset*.  This value tends to be higher than the **Trigger Threshold** explained below.  As the first pass is happening, the trigger value is being pulled up as the quad approaches the gate.  A relatively large value is needed to avoid false positives because of noise in the RSSI signal.

**Calibration Offset** - Basically "Gate Size". When calibrating on the first pass, this value will be subtracted from the peak RSSI value to act as the trigger value. If you are missing some pass records, raise this value. If you are getting extra pass records when looping close to the start gate at another point in the course, you can try lowering this value.

## Other Passes

**Trigger Threshold** - Similar to **Calibration Threshold** but used for all passes other than the calibration first pass. During a normal pass, the RSSI must fall below *trigger value - trigger threshold* in order to consider the pass complete. This value helps avoid multiple lap records during a single pass because of noise in the RSSI.  Raise this value if you get several pass records while passing the start gate.  Lower this value if the quad has to travel very far before a passing event is triggered.

**Note**: In all cases, the passing time is taken when the RSSI has reached it peak (when the quad should be closest to the sensor).  Even if larger threshold values cause there to be a delay in the lap being reported, the timing information will sill be correct.
