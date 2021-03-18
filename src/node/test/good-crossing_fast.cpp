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
  rssiNode.setFilter(&testFilter);
  State& state = rssiNode.getState();
  LastPass& lastPass = rssiNode.getLastPass();
  History& history = rssiNode.getHistory();
  rssiNode.start();

  state.activatedFlag = true;

  // prime the state with some background signal
  sendSignal(nano, 50);
  assertFalse(rssiNode.isStateValid());
  // more signal needed
  sendSignal(nano, 50);
  assertEqual(2*N_2*1000-1000, state.lastloopMicros);
  assertTrue(rssiNode.isStateValid());
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

  assertEqual(80, (int)history.prevRssiChange);
  assertEqual(130, (int)history.peak.rssi); // first upward trend
  assertEqual(timestamp(3), (int)history.peak.firstTime);
  assertEqual(0, (int)history.peak.duration);
  assertFalse(isNadirValid(history.nadir)); // no downward trend yet

  assertEqual(NONE, history.nextToSendType());

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

  assertEqual(-60, (int)history.prevRssiChange);
  assertEqual(130, (int)history.peak.rssi);
  assertEqual(timestamp(3), (int)history.peak.firstTime);
  assertEqual(time(1)-1, (int)history.peak.duration);
  assertEqual(70, (int)history.nadir.rssi); // first downward trend
  assertEqual(timestamp(4), (int)history.nadir.firstTime);
  assertEqual(0, (int)history.nadir.duration);

  assertEqual(130, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(timestamp(3), (int)history.sendBuffer->nextPeak().firstTime);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
  assertEqual(PEAK, history.nextToSendType());

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

  assertEqual(5, (int)history.prevRssiChange);
  assertEqual(75, (int)history.peak.rssi);
  assertEqual(timestamp(5), (int)history.peak.firstTime);
  assertEqual(0, (int)history.peak.duration);
  assertEqual(70, (int)history.nadir.rssi);
  assertEqual(timestamp(4), (int)history.nadir.firstTime);
  assertEqual(time(1)-1, (int)history.nadir.duration);

  assertEqual(130, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(timestamp(3), (int)history.sendBuffer->nextPeak().firstTime);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
  history.popNextToSend();
  assertEqual(70, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(timestamp(4), (int)history.sendBuffer->nextNadir().firstTime);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);

  // small fall
  sendSignal(nano, 60);

  assertEqual(75, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(timestamp(5), (int)history.sendBuffer->nextPeak().firstTime);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
  assertEqual(70, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(timestamp(4), (int)history.sendBuffer->nextNadir().firstTime);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  history.popNextToSend();
}

unittest_main()
