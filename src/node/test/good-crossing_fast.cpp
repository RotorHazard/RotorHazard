#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssi.h"
#include "util.h"

/**
 * Crossing lasting a single sample.
 */
unittest(fastCrossing) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  rssiInit();

  state.rxFreqSetFlag = true;

  // prime the state with some background signal
  sendSignal(nano, 50);
  assertFalse(rssiStateValid());
  // more signal needed
  sendSignal(nano, 50);
  assertEqual(2*N_2*1000-1000, state.lastloopMicros);
  assertTrue(rssiStateValid());
  assertEqual(50, (int)state.rssi);
  assertEqual(timestamp(2), (int)state.rssiTimestamp);
  assertEqual(50, (int)state.lastRssi);
  assertEqual(50, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);

  // enter
  sendSignal(nano, 130);
  assertEqual(130, (int)state.rssi);
  assertEqual(timestamp(3), (int)state.rssiTimestamp);
  assertEqual(50, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertTrue(state.crossing);

  assertEqual(130, (int)state.passRssiPeak);
  assertEqual(timestamp(3), (int)state.passRssiPeakFirstTime);
  assertEqual(timestamp(3), (int)state.passRssiPeakLastTime);
  assertEqual(50, (int)state.passRssiNadir);

  assertEqual(40, history.rssiChange);
  assertEqual(130, (int)history.peakRssi); // first upward trend
  assertEqual(timestamp(3), (int)history.peakFirstTime);
  assertEqual(timestamp(3), (int)history.peakLastTime);
  assertEqual(0, (int)history.nadirRssi); // no downward trend yet
  assertEqual(0, (int)history.nadirTime);

  assertFalse(isPeakValid(history.peakSendRssi));
  assertEqual(0, (int)history.nadirSendRssi);

  // exit
  sendSignal(nano, 70);
  assertEqual(70, (int)state.rssi);
  assertEqual(timestamp(4), (int)state.rssiTimestamp);
  assertEqual(130, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertFalse(state.crossing);

  assertFalse(isPeakValid(state.passRssiPeak)); // crossing/pass finished
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(-30, history.rssiChange);
  assertEqual(130, (int)history.peakRssi);
  assertEqual(timestamp(3), (int)history.peakFirstTime);
  assertEqual(timestamp(4)-1, (int)history.peakLastTime);
  assertEqual(70, (int)history.nadirRssi); // first downward trend
  assertEqual(timestamp(4), (int)history.nadirTime);

  assertEqual(130, (int)history.peakSendRssi);
  assertEqual(timestamp(3), (int)history.peakSendFirstTime);
  assertEqual(timestamp(4)-1, (int)history.peakSendLastTime);
  assertEqual(0, (int)history.nadirSendRssi);

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);

  // small rise
  sendSignal(nano, 75);
  assertEqual(75, (int)state.rssi);
  assertEqual(timestamp(5), (int)state.rssiTimestamp);
  assertEqual(70, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertFalse(state.crossing);

  assertEqual(0, (int)state.passRssiPeak);
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(2, history.rssiChange);
  assertEqual(75, (int)history.peakRssi);
  assertEqual(timestamp(5), (int)history.peakFirstTime);
  assertEqual(timestamp(5), (int)history.peakLastTime);
  assertEqual(70, (int)history.nadirRssi);
  assertEqual(timestamp(4), (int)history.nadirTime);

  assertEqual(130, (int)history.peakSendRssi);
  assertEqual(timestamp(3), (int)history.peakSendFirstTime);
  assertEqual(timestamp(4)-1, (int)history.peakSendLastTime);
  assertEqual(0, (int)history.nadirSendRssi);
  assertEqual(0, (int)history.nadirSendTime);

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);

  // small fall
  sendSignal(nano, 60);

  assertEqual(130, (int)history.peakSendRssi);
  assertEqual(timestamp(3), (int)history.peakSendFirstTime);
  assertEqual(timestamp(4)-1, (int)history.peakSendLastTime);
  assertEqual(70, (int)history.nadirSendRssi);
  assertEqual(timestamp(4), (int)history.nadirSendTime);
}

unittest_main()
