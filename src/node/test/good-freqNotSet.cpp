#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "util.h"

unittest(freqNotSet) {
  GodmodeState* nano = GODMODE();
  nano->reset();

  RssiNode::multiRssiNodeCount = 1;
  RssiNode *rssiNodePtr = &(RssiNode::rssiNodeArray[0]);
  rssiNodePtr->rssiInit();

  rssiNodePtr->setActivatedFlag(false);

  struct State & state = rssiNodePtr->getState();

  sendSignal(rssiNodePtr, nano, 43);
  assertFalse(rssiNodePtr->rssiStateValid());
  sendSignal(rssiNodePtr, nano, 43);
  assertEqual(2*N_2*1000-1000, state.lastloopMicros);
  assertFalse(rssiNodePtr->rssiStateValid());
  assertEqual(0, (int)state.rssi);
  assertEqual(0, (int)state.rssiTimestamp);
  assertEqual(0, (int)state.lastRssi);
  assertEqual(0, (int)state.nodeRssiPeak);
  assertEqual(255, (int)state.nodeRssiNadir);
}

unittest_main()
