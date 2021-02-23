#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssi.h"
#include "util.h"

unittest(freqNotSet) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  State& state = rssiNode.getState();
  LastPass& lastPass = rssiNode.getLastPass();
  History& history = rssiNode.getHistory();
  rssiNode.start();

  rssiNode.active = false;

  sendSignal(nano, 43);
  assertFalse(rssiNode.isStateValid());
  sendSignal(nano, 43);
  assertEqual(2*N_2*1000-1000, state.lastloopMicros);
  assertFalse(rssiNode.isStateValid());
  assertEqual(0, (int)state.rssi);
  assertEqual(0, (int)state.rssiTimestamp);
  assertEqual(0, (int)state.lastRssi);
  assertEqual(0, (int)state.nodeRssiPeak);
  assertEqual(255, (int)state.nodeRssiNadir);
}

unittest_main()
