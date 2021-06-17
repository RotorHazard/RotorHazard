#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "util.h"

unittest(freqNotSet) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  RssiNode& rssiNode = rssiRxs.getRssiNode(0);
  rssiNode.setFilter(&testFilter);
  State& state = rssiNode.getState();
  LastPass& lastPass = rssiNode.getLastPass();
  History& history = rssiNode.getHistory();

  rssiNode.active = false;
  rssiRxs.start(millis(), usclock);

  readRssi(nano, 43);
  assertFalse(rssiNode.isStateValid());
  readRssi(nano, 43);
  assertEqual(2*N_2*1000-1000, state.lastloopMicros);
  assertFalse(rssiNode.isStateValid());
  assertEqual(0, (int)state.rssi);
  assertEqual(0, (int)state.rssiTimestamp);
  assertEqual(0, (int)state.lastRssi);
  assertEqual(0, (int)state.nodeRssiPeak);
  assertEqual(255, (int)state.nodeRssiNadir);

  rssiNode.active = true;

  readRssi(nano, 43);
  readRssi(nano, 43);
  readRssi(nano, 43);
  assertTrue(rssiNode.isStateValid());
  assertEqual(43, (int)state.rssi);
  assertEqual(timestamp(5), (int)state.rssiTimestamp);
  assertEqual(43, (int)state.lastRssi);
  assertEqual(43, (int)state.nodeRssiPeak);
  assertEqual(43, (int)state.nodeRssiNadir);
}

unittest_main()
