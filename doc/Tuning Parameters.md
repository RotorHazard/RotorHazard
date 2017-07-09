# Auto Calibration and Sensor Tuning Parameters

The Delta5 Race Timer will auto-calibrate trigger values for the nodes during the first pass of the timing gate after starting each new race.

In order for auto-calibration to work, the system has to make a guess about when a quad passes the gate the first time. In theory, the RSSI will go up as you approach the timing gate and then fall as you travel away from it. In practice, there is a lot of noise and the value oscillates quite a bit.

Auto-calibration works best with the launch pads and start gate positioned in the middle of a straight away. You want a clean rise and fall of the RSSI value for the first pass and for each lap after.

### First Pass
To help with this explanation we're going to use some example values talking about one quad passing the gate. Let's assume that with the quad powered off the sensor is getting a background RSSI value of 100. With the quad powered and on the launch pad some distance away the RSSI is 150.

After the race start button is pressed and the quad starts moving towards the gate, the RSSI value will begin to increase from its initial value of 150. Eventually the quad passes the gate and the RSSI value starts to fall, let's say the Peak RSSI seen was 300. The trigger is set during this pass by subtracting the Calibration Offset (8) from the Peak RSSI (300), so the Trigger will be 292.

Now the system is waiting to detect when the quad has left the starting gate to confirm the Peak RSSI and Trigger values detected. It waits for the RSSI value to fall below the Trigger (292) minus Calibration Threshold (95) which is 197. Once the RSSI has dropped below 197 the system considers the first pass to be complete.

### Future Passes

The system is now waiting for the RSSI to rise above the Trigger value of 292 again. Once this happens it will consider the next gate pass to be happening. It will keep track of the Peak RSSI value seen and the time it happened, and continue to do so until the RSSI value falls below Trigger (292) minus Trigger Threshold (40) which is 252. Once the RSSI has dropped below 252, that gate pass is complete and the lap information is sent to the Raspberry Pi.

Note that the passing time is taken when the RSSI has reached it peak (when the quad should be closest to the sensor). Even if larger threshold values cause there to be a delay in the lap being reported, the timing information will sill be correct.

### Tuning

##### Calibration Offset
If you are missing some passes, it means the Calibration Offset value is too small and the quad is not reaching as high a peak RSSI value as was seen on the first pass. Increase Calibration Offset to ensure all laps are captured.

##### Calibration Threshold
Adds a buffer around the fluctuating RSSI value during the first pass. Increase the value if you are getting lower than expected trigger values because the fist pass has been triggered before actually crossing the gate. If you are not getting a pass record for the fist pass (and likely ever), decrease this value. A relatively large value is needed to avoid false positives because of noise in the RSSI signal.

##### Trigger Threshold
Increase this value if you get several pass records while passing the start gate. Lower this value if the quad has to travel very far before a passing event is triggered.
