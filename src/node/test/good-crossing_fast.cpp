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

  assertEqual(130, (int)state.passPeak.rssi);
  assertEqual(timestamp(3), (int)state.passPeak.firstTime);
  assertEqual(0, (int)state.passPeak.duration);
  assertEqual(50, (int)state.passRssiNadir);

  assertEqual(40, history.rssiChange);
  assertEqual(130, (int)history.peak.rssi); // first upward trend
  assertEqual(timestamp(3), (int)history.peak.firstTime);
  assertEqual(0, (int)history.peak.duration);
  assertEqual(0, (int)history.nadir.rssi); // no downward trend yet
  assertEqual(0, (int)history.nadir.firstTime);
  assertEqual(0, (int)history.nadir.duration);

  assertFalse(isPeakValid(history.peakSend));
  assertEqual(0, (int)history.nadirSend.rssi);

  // exit
  sendSignal(nano, 70);
  assertEqual(70, (int)state.rssi);
  assertEqual(timestamp(4), (int)state.rssiTimestamp);
  assertEqual(130, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertFalse(state.crossing);

  assertFalse(isPeakValid(state.passPeak)); // crossing/pass finished
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(-30, history.rssiChange);
  assertEqual(130, (int)history.peak.rssi);
  assertEqual(timestamp(3), (int)history.peak.firstTime);
  assertEqual(time(1)-1, (int)history.peak.duration);
  assertEqual(70, (int)history.nadir.rssi); // first downward trend
  assertEqual(timestamp(4), (int)history.nadir.firstTime);
  assertEqual(0, (int)history.nadir.duration);

  assertEqual(130, (int)history.peakSend.rssi);
  assertEqual(timestamp(3), (int)history.peakSend.firstTime);
  assertEqual(time(1)-1, (int)history.peakSend.duration);
  assertEqual(0, (int)history.nadirSend.rssi);

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

  assertEqual(0, (int)state.passPeak.rssi);
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(2, history.rssiChange);
  assertEqual(75, (int)history.peak.rssi);
  assertEqual(timestamp(5), (int)history.peak.firstTime);
  assertEqual(0, (int)history.peak.duration);
  assertEqual(70, (int)history.nadir.rssi);
  assertEqual(timestamp(4), (int)history.nadir.firstTime);
  assertEqual(time(1)-1, (int)history.nadir.duration);

  assertEqual(130, (int)history.peakSend.rssi);
  assertEqual(timestamp(3), (int)history.peakSend.firstTime);
  assertEqual(time(1)-1, (int)history.peakSend.duration);
  assertEqual(0, (int)history.nadirSend.rssi);
  assertEqual(0, (int)history.nadirSend.firstTime);
  assertEqual(0, (int)history.nadirSend.duration);

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);

  // small fall
  sendSignal(nano, 60);

  assertEqual(130, (int)history.peakSend.rssi);
  assertEqual(timestamp(3), (int)history.peakSend.firstTime);
  assertEqual(time(1)-1, (int)history.peakSend.duration);
  assertEqual(70, (int)history.nadirSend.rssi);
  assertEqual(timestamp(4), (int)history.nadirSend.firstTime);
  assertEqual(time(1)-1, (int)history.nadirSend.duration);
}

unittest(prolonged_crossing) {
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
  assertLessOrEqual(1, duration);
  for(int i=0; i<duration; i++) {
      sendSignal(nano, 130);
  }

  assertEqual(130, (int)state.rssi);
  assertEqual(timestamp(3+duration), (int)state.rssiTimestamp);
  assertEqual(130, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertEqual(80, history.rssiChange);
  assertTrue(state.crossing);

  assertEqual(130, (int)state.passRssiPeak);
  assertEqual(timestamp(3), (int)state.passRssiPeakFirstTime);
  assertEqual(timestamp(3+duration), (int)state.passRssiPeakLastTime);
  assertEqual(130, (int)history.peakRssi); // first upward trend
  assertEqual(50, (int)history.nadirRssi); // from prolonged background signal
  assertEqual(timestamp(3), (int)history.peakFirstTime);
  assertEqual(timestamp(3+duration), (int)history.peakLastTime);

  assertEqual(130, (int)history.peakSendRssi);
  assertEqual(timestamp(3), (int)history.peakSendFirstTime);
  assertEqual(timestamp(4)-1, (int)history.peakSendLastTime); // wrong
  assertEqual(timestamp(2)-1, (int)history.nadirTime);
  assertEqual(50, (int)history.nadirSendRssi);
  assertEqual(timestamp(2)-1, (int)history.nadirSendTime);

  // exit
  sendSignal(nano, 70);
  assertEqual(70, (int)state.rssi);
  assertEqual(timestamp(4+duration), (int)state.rssiTimestamp);
  assertEqual(130, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertEqual(-60, history.rssiChange);
  assertFalse(state.crossing);

  assertEqual(0, (int)state.passRssiPeak); // crossing/pass finished
  assertEqual(timestamp(3), (int)state.passRssiPeakFirstTime);
  assertEqual(timestamp(4+duration)-1, (int)state.passRssiPeakLastTime);
  assertEqual(130, (int)history.peakRssi);
  assertEqual(70, (int)history.nadirRssi); // first downward trend

  assertEqual(130, (int)history.peakSendRssi);
  assertEqual(timestamp(3), (int)history.peakSendFirstTime);
  assertEqual(timestamp(4)-1, (int)history.peakSendLastTime); // wrong
  assertEqual(timestamp(4+duration), (int)history.nadirTime);
  assertEqual(50, (int)history.nadirSendRssi);
  assertEqual(timestamp(2)-1, (int)history.nadirSendTime);

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4+duration)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);
}

unittest_main()

