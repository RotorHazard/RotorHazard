#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "util.h"

/**
 * Crossing lasting a single sample.
 */
unittest(fastCrossing) {
  GodmodeState* nano = GODMODE();
  nano->reset();

  RssiNode::multiRssiNodeCount = 1;
  RssiNode *rssiNodePtr = &(RssiNode::rssiNodeArray[0]);
  rssiNodePtr->rssiSetFilter(&testFilter);
  rssiNodePtr->rssiInit();

  rssiNodePtr->setActivatedFlag(true);

  // prime the state with some background signal
  sendSignal(rssiNodePtr, nano, 50);
  assertFalse(rssiNodePtr->rssiStateValid());

  struct State & state = rssiNodePtr->getState();
  struct History & history = rssiNodePtr->getHistory();
  struct LastPass & lastPass = rssiNodePtr->getLastPass();

  // more signal needed
  sendSignal(rssiNodePtr, nano, 50);
  assertEqual(2*N_2*1000-1000, state.lastloopMicros);
  assertTrue(rssiNodePtr->rssiStateValid());
  assertEqual(50, (int)state.rssi);
  assertEqual(timestamp(2), (int)state.rssiTimestamp);
  assertEqual(50, (int)state.lastRssi);
  assertEqual(50, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);

  // enter
  sendSignal(rssiNodePtr, nano, 130);
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

  assertEqual(80, (int)history.rssiChange);
  assertEqual(130, (int)history.peak.rssi); // first upward trend
  assertEqual(timestamp(3), (int)history.peak.firstTime);
  assertEqual(0, (int)history.peak.duration);
  assertFalse(isNadirValid(history.nadir)); // no downward trend yet

  assertTrue(history.peakSend->isEmpty());
  assertTrue(history.nadirSend->isEmpty());

  // exit
  sendSignal(rssiNodePtr, nano, 70);
  assertEqual(70, (int)state.rssi);
  assertEqual(timestamp(4), (int)state.rssiTimestamp);
  assertEqual(130, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertFalse(state.crossing);

  assertFalse(isPeakValid(state.passPeak)); // crossing/pass finished
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(-60, (int)history.rssiChange);
  assertEqual(130, (int)history.peak.rssi);
  assertEqual(timestamp(3), (int)history.peak.firstTime);
  assertEqual(time(1)-1, (int)history.peak.duration);
  assertEqual(70, (int)history.nadir.rssi); // first downward trend
  assertEqual(timestamp(4), (int)history.nadir.firstTime);
  assertEqual(0, (int)history.nadir.duration);

  assertEqual(130, (int)history.peakSend->first().rssi);
  assertEqual(timestamp(3), (int)history.peakSend->first().firstTime);
  assertEqual(time(1)-1, (int)history.peakSend->first().duration);
  assertTrue(history.nadirSend->isEmpty());

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);

  // small rise
  sendSignal(rssiNodePtr, nano, 75);
  assertEqual(75, (int)state.rssi);
  assertEqual(timestamp(5), (int)state.rssiTimestamp);
  assertEqual(70, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertFalse(state.crossing);

  assertEqual(0, (int)state.passPeak.rssi);
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(5, (int)history.rssiChange);
  assertEqual(75, (int)history.peak.rssi);
  assertEqual(timestamp(5), (int)history.peak.firstTime);
  assertEqual(0, (int)history.peak.duration);
  assertEqual(70, (int)history.nadir.rssi);
  assertEqual(timestamp(4), (int)history.nadir.firstTime);
  assertEqual(time(1)-1, (int)history.nadir.duration);

  assertEqual(130, (int)history.peakSend->first().rssi);
  assertEqual(timestamp(3), (int)history.peakSend->first().firstTime);
  assertEqual(time(1)-1, (int)history.peakSend->first().duration);
  history.peakSend->removeFirst();
  assertEqual(70, (int)history.nadirSend->first().rssi);
  assertEqual(timestamp(4), (int)history.nadirSend->first().firstTime);
  assertEqual(time(1)-1, (int)history.nadirSend->first().duration);

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);

  // small fall
  sendSignal(rssiNodePtr, nano, 60);

  assertEqual(75, (int)history.peakSend->first().rssi);
  assertEqual(timestamp(5), (int)history.peakSend->first().firstTime);
  assertEqual(time(1)-1, (int)history.peakSend->first().duration);
  assertEqual(70, (int)history.nadirSend->first().rssi);
  assertEqual(timestamp(4), (int)history.nadirSend->first().firstTime);
  assertEqual(time(1)-1, (int)history.nadirSend->first().duration);
  history.nadirSend->removeFirst();
}

unittest_main()
