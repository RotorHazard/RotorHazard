#include "Arduino.h"
#include "FastRunningMedian.h"
#include "rssi.h"

struct Settings settings;
struct State state;
struct History history;
struct LastPass lastPass;

FastRunningMedian<rssi_t, SmoothingSamples, 0> rssiMedian;

mtime_t volatile SmoothingTimestamps[SmoothingTimestampSize];
uint8_t SmoothingTimestampsIndex = 0;

void rssiInit()
{
      lastPass.rssiPeak = 0;
      lastPass.lap = 0;
      lastPass.timestamp = 0;
      state.lastloopMicros = micros();
}

bool rssiStateValid()
{
      return state.nodeRssiNadir <= state.rssiSmoothed && state.rssiSmoothed <= state.nodeRssiPeak;
}

void rssiStateReset()
{
      state.nodeRssiPeak = 0;
      state.nodeRssiNadir = MAX_RSSI;
}

void rssiProcess(rssi_t rssi, mtime_t millis)
{
      rssiMedian.addValue(rssi);

      SmoothingTimestamps[SmoothingTimestampsIndex] = millis;
      SmoothingTimestampsIndex++;
      if (SmoothingTimestampsIndex >= SmoothingTimestampSize) {
    	  SmoothingTimestampsIndex = 0;
      }

      if (rssiMedian.isFilled() && state.rxFreqSetFlag)
      {  //don't start operations until after first WRITE_FREQUENCY command is received

	  state.lastRssiSmoothed = state.rssiSmoothed;
	  state.rssiSmoothed = rssiMedian.getMedian(); // retrieve the median
	  state.rssiTimestamp = SmoothingTimestamps[SmoothingTimestampsIndex];

	  int rssiChange = state.rssiSmoothed - state.lastRssiSmoothed;
	  // update history
	  if (rssiChange > 0) { // RSSI is rising
	    history.peakRssi = state.rssiSmoothed;
	    history.peakFirstTime = history.peakLastTime = state.rssiTimestamp;

	    // if RSSI was falling, but it's rising now, we found a nadir
	    // copy the values to be sent in the next loop
	    if (history.rssiChange < 0) { // is falling
	      // declare a new nadir if we don't have one or if the new one is lower
	      if (!history.nadirSend || history.nadirRssi < history.nadirSendRssi) {
		history.nadirSend = true;
		history.nadirSendRssi = history.nadirRssi;
		history.nadirSendTime = history.nadirTime;
	      }
	    }

	  } else if (rssiChange < 0) { // RSSI is falling
	    // whenever history is falling, record the time and value as a nadir
	    history.nadirRssi = state.rssiSmoothed;
	    history.nadirTime = state.rssiTimestamp;

	    // if RSSI was rising, but it's falling now, we found a peak
	    // copy the values to be sent in the next loop
	    if (history.rssiChange > 0) { // is rising
	      // declare a new peak if we don't have one or if the new one is higher
	      if (!history.peakSend || history.peakRssi > history.peakSendRssi) {
		history.peakSend = true;
		history.peakSendRssi = history.peakRssi;
		history.peakSendFirstTime = history.peakFirstTime;
		history.peakSendLastTime = history.peakLastTime;
	      }
	    }

	  } else { // RSSI is equal
	    // we don't need to track first and last times if it's a nadir
	    if (history.rssiChange > 0) { // is rising
	      history.peakLastTime = state.rssiTimestamp;
	    }
	  }

	  if (rssiChange != 0) { // filter out plateaus
	      // clamp to prevent overflow
	      history.rssiChange = constrain(rssiChange, -127, 127);
	  }

	  // Keep track of peak (smoothed) rssi
	  if (state.rssiSmoothed > state.nodeRssiPeak)
	  {
	      state.nodeRssiPeak = state.rssiSmoothed;
	      Serial.print(F("New nodeRssiPeak = "));
	      Serial.println(state.nodeRssiPeak);
	  }

	  if (state.rssiSmoothed < state.nodeRssiNadir)
	  {
	      state.nodeRssiNadir = state.rssiSmoothed;
	      Serial.print(F("New nodeRssiNadir = "));
	      Serial.println(state.nodeRssiNadir);
	  }

	  if ((!state.crossing) && state.rssiSmoothed >= settings.enterAtLevel)
	  {
	      state.crossing = true;  // quad is going through the gate (lap pass starting)
	      Serial.println(F("Crossing = True"));
	  }

	  // Find the peak rssi and the time it occured during a crossing event
	  if (state.rssiSmoothed >= state.passRssiPeakRaw)
	  {
	      // if at max peak for more than one iteration then track first
	      //  and last timestamp so middle-timestamp value can be returned
	      state.passRssiPeakRawLastTime = state.rssiTimestamp;

	      if (state.rssiSmoothed > state.passRssiPeakRaw)
	      {
		  // this is first time this peak-raw-RSSI value was seen, so save value and timestamp
		  state.passRssiPeakRaw = state.rssiSmoothed;
		  state.passRssiPeakRawTime = state.passRssiPeakRawLastTime;
	      }
	  }

	  // track lowest smoothed rssi seen since end of last pass
	  state.passRssiNadir = min(state.rssiSmoothed, state.passRssiNadir);

	  if (state.crossing)
	  {  //lap pass is in progress

	      // track RSSI peak for current lap pass
	      state.passRssiPeak = max(state.rssiSmoothed, state.passRssiPeak);

	      // see if quad has left the gate
	      if (state.rssiSmoothed < settings.exitAtLevel)
	      {
		  Serial.println(F("Crossing = False"));
		  rssiEndCrossing();
	      }
	  }
      }

      // Calculate the time it takes to run the main loop
      utime_t loopMicros = micros();
      state.loopTimeMicros = loopMicros - state.lastloopMicros;
      state.lastloopMicros = loopMicros;

      // Status LED
      if (state.crossing ||  // on while crossing
	  (millis / 100) % 10 == 0 // blink
	) {
	digitalWrite(LED_BUILTIN, HIGH);
      } else {
	digitalWrite(LED_BUILTIN, LOW);
      }
}

// Function called when crossing ends (by RSSI or I2C command)
void rssiEndCrossing() {
    // save values for lap pass
    lastPass.rssiPeak = state.passRssiPeak;
    // lap timestamp is between first and last peak RSSI
    lastPass.timestamp = (state.passRssiPeakRawLastTime + state.passRssiPeakRawTime) / 2;
    lastPass.rssiNadir = state.passRssiNadir;
    lastPass.lap = lastPass.lap + 1;

    // reset lap-pass variables
    state.crossing = false;
    state.passRssiPeakRaw = 0;
    state.passRssiPeak = 0;
    state.passRssiNadir = MAX_RSSI;
}
