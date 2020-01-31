#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssi.h"
#include "util.h"

/**
 * Tests history buffer.
 */
unittest(historyBuffer) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  rssiInit();

  state.activatedFlag = true;

  // prime the state with some background signal
  sendSignal(nano, 60);
  sendSignal(nano, 40);

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(60, (int)history.peakSend.rssi);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(40, (int)history.nadirSend.rssi);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(60, (int)history.peakSend.rssi);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(40, (int)history.nadirSend.rssi);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(80, (int)history.peakSend.rssi);
  assertEqual(time(1)-1, (int)history.peakSend.duration);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(20, (int)history.nadirSend.rssi);
  assertEqual(time(1)-1, (int)history.nadirSend.duration);

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(80, (int)history.peakSend.rssi);
  // merged with current peakSend
  assertEqual(time(3)-1, (int)history.peakSend.duration);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(20, (int)history.nadirSend.rssi);
  // merged with current nadirSend
  assertEqual(time(3)-1, (int)history.nadirSend.duration);

  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  // current large peak in peakSend is kept over new smaller peak
  assertEqual(80, (int)history.peakSend.rssi);
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  // current large nadir in nadirSend is kept over new smaller nadir
  assertEqual(20, (int)history.nadirSend.rssi);
}

unittest_main()
