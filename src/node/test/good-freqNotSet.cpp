#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssi.h"
#include "util.h"

unittest(freqNotSet) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  rssiInit();

  state.rxFreqSetFlag = false;

  sendSignal(nano, 43);
  assertFalse(rssiStateValid());
  sendSignal(nano, 43);
  assertEqual(2*N_2*1000-1000, state.lastloopMicros);
  assertFalse(rssiStateValid());
  assertEqual(0, (int)state.rssi);
  assertEqual(0, (int)state.rssiTimestamp);
  assertEqual(0, (int)state.lastRssi);
  assertEqual(0, (int)state.nodeRssiPeak);
  assertEqual(255, (int)state.nodeRssiNadir);
}

unittest_main()
