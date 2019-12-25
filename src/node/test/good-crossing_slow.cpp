#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssi.h"
#include "util.h"

/**
 * Crossing lasting several samples.
 */
unittest(slowCrossing) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  rssiInit();

  state.rxFreqSetFlag = true;

  // prime the state with some background signal
  sendSignal(nano, 50);
  sendSignal(nano, 50);
  assertTrue(rssiStateValid());

  // enter
  sendSignal(nano, 130);
  int duration = 3;
  for(int i=0; i<duration; i++) {
      sendSignal(nano, 130);
  }

  assertEqual(130, (int)state.rssi);
  assertEqual(timestamp(3+duration), (int)state.rssiTimestamp);
  if (duration > 0) {
      assertEqual(130, (int)state.lastRssi);
  } else {
      assertEqual(50, (int)state.lastRssi);
  }
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertTrue(state.crossing);

  assertEqual(130, (int)state.passRssiPeak);
  assertEqual(timestamp(3), (int)state.passRssiPeakFirstTime);
  assertEqual(timestamp(3+duration), (int)state.passRssiPeakLastTime);
  assertEqual(50, (int)state.passRssiNadir);

  if (duration > 0) {
      assertEqual(0, history.rssiChange);
  } else {
      assertEqual(40, history.rssiChange);
  }
  assertEqual(130, (int)history.peakRssi); // first upward trend
  assertEqual(timestamp(3), (int)history.peakFirstTime);
  assertEqual(timestamp(3+duration), (int)history.peakLastTime);
  assertEqual(0, (int)history.nadirRssi); // no downward trend yet
  assertEqual(0, (int)history.nadirTime);

  assertFalse(isPeakValid(history.peakSendRssi));
  assertEqual(0, (int)history.nadirSendRssi);

  // exit
  sendSignal(nano, 70);
  assertEqual(70, (int)state.rssi);
  assertEqual(timestamp(4+duration), (int)state.rssiTimestamp);
  assertEqual(130, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertFalse(state.crossing);

  assertFalse(isPeakValid(state.passRssiPeak)); // crossing/pass finished
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(-30, history.rssiChange);
  assertEqual(130, (int)history.peakRssi);
  assertEqual(timestamp(3), (int)history.peakFirstTime);
  assertEqual(timestamp(4+duration)-1, (int)history.peakLastTime);
  assertEqual(70, (int)history.nadirRssi); // first downward trend
  assertEqual(timestamp(4+duration), (int)history.nadirTime);

  assertEqual(130, (int)history.peakSendRssi);
  assertEqual(timestamp(3), (int)history.peakSendFirstTime);
  assertEqual(timestamp(4+duration)-1, (int)history.peakSendLastTime);
  assertEqual(0, (int)history.nadirSendRssi);

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4+duration)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);
}

unittest_main()
