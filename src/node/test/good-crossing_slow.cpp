#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "util.h"

/**
 * Crossing lasting several samples.
 */
unittest(slowCrossing) {
  GodmodeState* nano = GODMODE();
  nano->reset();

  RssiNode::multiRssiNodeCount = 1;
  RssiNode *rssiNodePtr = &(RssiNode::rssiNodeArray[0]);
  rssiNodePtr->rssiSetFilter(&testFilter);
  rssiNodePtr->rssiInit();

  rssiNodePtr->setActivatedFlag(true);

  // prime the state with some background signal
  sendSignal(rssiNodePtr, nano, 50);
  sendSignal(rssiNodePtr, nano, 50);
  assertTrue(rssiNodePtr->rssiStateValid());

  // enter
  sendSignal(rssiNodePtr, nano, 130);
  int duration = 3;
  for(int i=0; i<duration; i++) {
      sendSignal(rssiNodePtr, nano, 130);
  }

  struct State & state = rssiNodePtr->getState();
  struct History & history = rssiNodePtr->getHistory();
  struct LastPass & lastPass = rssiNodePtr->getLastPass();

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
      assertEqual(0, (int)history.rssiChange);
  } else {
      assertEqual(80, (int)history.rssiChange);
  }
  assertEqual(130, (int)history.peak.rssi); // first upward trend
  assertEqual(timestamp(3), (int)history.peak.firstTime);
  assertEqual(time(duration), (int)history.peak.duration);
  assertFalse(isNadirValid(history.nadir)); // no downward trend yet

  assertTrue(history.peakSend->isEmpty());
  assertTrue(history.nadirSend->isEmpty());

  // exit
  sendSignal(rssiNodePtr, nano, 70);
  assertEqual(70, (int)state.rssi);
  assertEqual(timestamp(4+duration), (int)state.rssiTimestamp);
  assertEqual(130, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertFalse(state.crossing);

  assertFalse(isPeakValid(state.passPeak)); // crossing/pass finished
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(-60, (int)history.rssiChange);
  assertEqual(130, (int)history.peak.rssi);
  assertEqual(timestamp(3), (int)history.peak.firstTime);
  assertEqual(time(1+duration)-1, (int)history.peak.duration);
  assertEqual(70, (int)history.nadir.rssi); // first downward trend
  assertEqual(timestamp(4+duration), (int)history.nadir.firstTime);
  assertEqual(0, (int)history.nadir.duration);

  assertEqual(130, (int)history.peakSend->first().rssi);
  assertEqual(timestamp(3), (int)history.peakSend->first().firstTime);
  assertEqual(time(1+duration)-1, (int)history.peakSend->first().duration);
  assertTrue(history.nadirSend->isEmpty());

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4+duration)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);
}

unittest_main()
