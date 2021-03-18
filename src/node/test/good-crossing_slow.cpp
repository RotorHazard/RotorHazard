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
  rssiNode.setFilter(&testFilter);
  State& state = rssiNode.getState();
  LastPass& lastPass = rssiNode.getLastPass();
  History& history = rssiNode.getHistory();
  rssiNode.start();

  state.activatedFlag = true;

  // prime the state with some background signal
  sendSignal(nano, 50);
  sendSignal(nano, 50);
  assertTrue(rssiNode.isStateValid());

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

  assertEqual(130, (int)state.passPeak.rssi);
  assertEqual(timestamp(3), (int)state.passPeak.firstTime);
  assertEqual(time(duration), (int)state.passPeak.duration);
  assertEqual(50, (int)state.passRssiNadir);

  if (duration > 0) {
      assertEqual(0, (int)history.prevRssiChange);
  } else {
      assertEqual(80, (int)history.prevRssiChange);
  }
  assertEqual(130, (int)history.peak.rssi); // first upward trend
  assertEqual(timestamp(3), (int)history.peak.firstTime);
  assertEqual(time(duration), (int)history.peak.duration);
  assertFalse(isNadirValid(history.nadir)); // no downward trend yet

  assertEqual(NONE, history.nextToSendType());

  // exit
  sendSignal(nano, 70);
  assertEqual(70, (int)state.rssi);
  assertEqual(timestamp(4+duration), (int)state.rssiTimestamp);
  assertEqual(130, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertFalse(state.crossing);

  assertFalse(isPeakValid(state.passPeak)); // crossing/pass finished
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(-60, (int)history.prevRssiChange);
  assertEqual(130, (int)history.peak.rssi);
  assertEqual(timestamp(3), (int)history.peak.firstTime);
  assertEqual(time(1+duration)-1, (int)history.peak.duration);
  assertEqual(70, (int)history.nadir.rssi); // first downward trend
  assertEqual(timestamp(4+duration), (int)history.nadir.firstTime);
  assertEqual(0, (int)history.nadir.duration);

  assertEqual(130, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(timestamp(3), (int)history.sendBuffer->nextPeak().firstTime);
  assertEqual(time(1+duration)-1, (int)history.sendBuffer->nextPeak().duration);
  assertEqual(PEAK, history.nextToSendType());

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4+duration)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);
}

unittest_main()
