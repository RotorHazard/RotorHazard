#ifdef __TEST__
  #define ATOMIC_BLOCK(x)
  #define ATOMIC_RESTORESTATE
#else
  #include <util/atomic.h>
#endif
#include "Arduino.h"
#include "FastRunningMedian.h"
#include "rssi.h"

struct Settings settings;
struct State state;
struct History history;
struct LastPass lastPass;

FastRunningMedian<rssi_t, SmoothingSamples, 0> rssiMedian;

mtime_t SmoothingTimestamps[SmoothingTimestampSize];
uint8_t SmoothingTimestampsIndex = 0;

void rssiInit()
{
  rssiMedian.init();
  state.lastloopMicros = micros();
}

bool rssiStateValid()
{
  return state.nodeRssiNadir <= state.rssi && state.rssi <= state.nodeRssiPeak;
}

void rssiStateReset()
{
  state.nodeRssiPeak = 0;
  state.nodeRssiNadir = MAX_RSSI;
}

static void bufferHistoricPeak(bool force) {
  if (history.hasPendingPeak && (!isPeakValid(history.peakSendRssi) || force)) {
      ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
	history.peakSendRssi = history.peakRssi;
	history.peakSendFirstTime = history.peakFirstTime;
	history.peakSendLastTime = history.peakLastTime;
      }
      history.hasPendingPeak = false;
  }
}

static void bufferHistoricNadir(bool force) {
  if (history.hasPendingNadir && (!isNadirValid(history.nadirSendRssi) || force)) {
      ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
	history.nadirSendRssi = history.nadirRssi;
	history.nadirSendTime = history.nadirTime;
      }
      history.hasPendingNadir = false;
  }
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

      state.lastRssi = state.rssi;
      state.rssi = rssiMedian.getMedian(); // retrieve the median
      state.rssiTimestamp = SmoothingTimestamps[SmoothingTimestampsIndex];

      /*** update history ***/

      int rssiChange = (state.rssi - state.lastRssi)/2; // rescale to remove some jitter
      if (rssiChange > 0) { // RSSI is rising
	  // must buffer latest peak to prevent losing it (overwriting any unsent peak)
	  bufferHistoricPeak(true);

	  history.peakRssi = state.rssi;
	  history.peakFirstTime = history.peakLastTime = state.rssiTimestamp;

	  // if RSSI was falling or unchanged, but it's rising now, we found a nadir
	  // copy the values to be sent in the next loop
	  if (history.rssiChange <= 0) { // was falling or unchanged
	      // declare a new nadir
	      history.hasPendingNadir = true;
	  }

      } else if (rssiChange < 0) { // RSSI is falling
	  // must buffer latest nadir to prevent losing it (overwriting any unsent nadir)
	  bufferHistoricNadir(true);

	  // whenever history is falling, record the time and value as a nadir
	  history.nadirRssi = state.rssi;
	  history.nadirTime = state.rssiTimestamp;

	  // if RSSI was rising or unchanged, but it's falling now, we found a peak
	  // copy the values to be sent in the next loop
	  if (history.rssiChange >= 0) { // was rising or unchanged
	      // declare a new peak
	      history.hasPendingPeak = true;
	  }

      } else { // RSSI is equal
	  // we don't need to track first and last times if it's a nadir
	  if (state.rssi == history.peakRssi) { // is peak
	      history.peakLastTime = state.rssiTimestamp;
	  }
      }

      // clamp to prevent overflow
      history.rssiChange = constrain(rssiChange, -127, 127);

      // try to buffer latest peak/nadir (don't overwrite any unsent peak/nadir)
      bufferHistoricPeak(false);
      bufferHistoricNadir(false);

      /*** node lifetime RSSI max/min ***/

      if (state.rssi > state.nodeRssiPeak) {
	  state.nodeRssiPeak = state.rssi;
	  Serial.print(F("New nodeRssiPeak = "));
	  Serial.println(state.nodeRssiPeak);
      }

      if (state.rssi < state.nodeRssiNadir) {
	  state.nodeRssiNadir = state.rssi;
	  Serial.print(F("New nodeRssiNadir = "));
	  Serial.println(state.nodeRssiNadir);
      }

      /*** crossing transition ***/

      if ((!state.crossing) && state.rssi >= settings.enterAtLevel) {
	  state.crossing = true;  // quad is going through the gate (lap pass starting)
	  Serial.println(F("Crossing = True"));
      } else if (state.crossing && state.rssi < settings.exitAtLevel) {
	  // quad has left the gate
	  rssiEndCrossing();
	  Serial.println(F("Crossing = False"));
      }

      /*** pass processing **/

      if (state.crossing) { //lap pass is in progress
	  // Find the peak rssi and the time it occured during a crossing event
	  if (state.rssi > state.passRssiPeak) {
	      // this is first time this peak RSSI value was seen, so save value and timestamp
	      state.passRssiPeak = state.rssi;
	      state.passRssiPeakFirstTime = state.passRssiPeakLastTime = state.rssiTimestamp;
	  } else if (state.rssi == state.passRssiPeak) {
	      // if at max peak for more than one iteration then track first
	      //  and last timestamp so middle-timestamp value can be returned
	      state.passRssiPeakLastTime = state.rssiTimestamp;
	  }
      } else {
	  // track lowest rssi seen since end of last pass
	  state.passRssiNadir = min(state.rssi, state.passRssiNadir);
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
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    lastPass.rssiPeak = state.passRssiPeak;
    // lap timestamp is between first and last peak RSSI
    lastPass.timestamp = (state.passRssiPeakLastTime + state.passRssiPeakFirstTime) / 2;
    lastPass.rssiNadir = state.passRssiNadir;
    lastPass.lap = lastPass.lap + 1;
  }

  // reset lap-pass variables
  state.crossing = false;
  state.passRssiPeak = 0;
  state.passRssiNadir = MAX_RSSI;
}
