#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssi.h"
#include "util.h"
#include "../util/single-sendbuffer.h"

unittest(historyBuffer_prefers_biggest_peak) {
    Extremum e = {23, 2, 100};
    SinglePeakSendBuffer buffer;
    assertTrue(buffer.addIfAvailable(e));
    e.rssi = 20;
    buffer.addOrDiscard(e);
    e = buffer.first();
    assertEqual(23, (int)e.rssi);
    e.rssi = 27;
    buffer.addOrDiscard(e);
    e = buffer.first();
    assertEqual(27, (int)e.rssi);
}

unittest(historyBuffer_merges_peak) {
    Extremum e = {23, 2, 100};
    SinglePeakSendBuffer buffer;
    assertTrue(buffer.addIfAvailable(e));
    e.firstTime = 102, e.duration = 10;
    buffer.addOrDiscard(e);
    e = buffer.first();
    assertEqual(23, (int)e.rssi);
    assertEqual(2, e.firstTime);
    assertEqual(110, e.duration);
}

unittest(historyBuffer_prefers_smallest_nadir) {
    Extremum e = {23, 2, 100};
    SingleNadirSendBuffer buffer;
    assertTrue(buffer.addIfAvailable(e));
    e.rssi = 27;
    buffer.addOrDiscard(e);
    e = buffer.first();
    assertEqual(23, (int)e.rssi);
    e.rssi = 20;
    buffer.addOrDiscard(e);
    e = buffer.first();
    assertEqual(20, (int)e.rssi);
}

unittest(historyBuffer_merges_nadir) {
    Extremum e = {23, 2, 100};
    SingleNadirSendBuffer buffer;
    assertTrue(buffer.addIfAvailable(e));
    e.firstTime = 102, e.duration = 10;
    buffer.addOrDiscard(e);
    e = buffer.first();
    assertEqual(23, (int)e.rssi);
    assertEqual(2, e.firstTime);
    assertEqual(110, e.duration);
}

/**
 * Tests history buffer.
 */
unittest(historyBuffer_withoutReads) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  rssiNode.setFilter(&testFilter);
  State& state = rssiNode.getState();
  History& history = rssiNode.getHistory();
  SinglePeakSendBuffer peakBuffer;
  SingleNadirSendBuffer nadirBuffer;
  history.setSendBuffers(&peakBuffer, &nadirBuffer);
  rssiNode.start();
  rssiNode.resetState();
  nano->micros += 40000; // settle time

  assertFalse(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());

  state.activatedFlag = true;

  // prime the state with some background signal
  sendSignal(nano, 60);
  sendSignal(nano, 40);

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(60, (int)history.peakSend->first().rssi);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(40, (int)history.nadirSend->first().rssi);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(60, (int)history.peakSend->first().rssi);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(40, (int)history.nadirSend->first().rssi);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertFalse(history.canSendPeakNext());
  assertTrue(history.canSendNadirNext());
  assertEqual(80, (int)history.peakSend->first().rssi);
  assertEqual(time(1)-1, (int)history.peakSend->first().duration);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(20, (int)history.nadirSend->first().rssi);
  assertEqual(time(1)-1, (int)history.nadirSend->first().duration);

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(80, (int)history.peakSend->first().rssi);
  // merged with current peakSend
  assertEqual(time(3)-1, (int)history.peakSend->first().duration);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(20, (int)history.nadirSend->first().rssi);
  // merged with current nadirSend
  assertEqual(time(3)-1, (int)history.nadirSend->first().duration);

  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  // current large peak in peakSend is kept over new smaller peak
  assertEqual(80, (int)history.peakSend->first().rssi);
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  // current large nadir in nadirSend is kept over new smaller nadir
  assertEqual(20, (int)history.nadirSend->first().rssi);
}

/**
 * Tests history buffer.
 */
unittest(historyBuffer_withReads) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  rssiNode.setFilter(&testFilter);
  State& state = rssiNode.getState();
  History& history = rssiNode.getHistory();
  SinglePeakSendBuffer peakBuffer;
  SingleNadirSendBuffer nadirBuffer;
  history.setSendBuffers(&peakBuffer, &nadirBuffer);
  rssiNode.start();
  rssiNode.resetState();
  nano->micros += 40000; // settle time

  assertFalse(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());

  state.activatedFlag = true;

  // prime the state with some background signal
  sendSignal(nano, 60);
  sendSignal(nano, 40);

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(60, (int)history.peakSend->first().rssi);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(40, (int)history.nadirSend->first().rssi);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(60, (int)history.peakSend->first().rssi);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(40, (int)history.nadirSend->first().rssi);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertFalse(history.canSendPeakNext());
  assertTrue(history.canSendNadirNext());
  assertEqual(80, (int)history.peakSend->first().rssi);
  assertEqual(time(1)-1, (int)history.peakSend->first().duration);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(20, (int)history.nadirSend->first().rssi);
  assertEqual(time(1)-1, (int)history.nadirSend->first().duration);

  history.peakSend->removeFirst();

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertFalse(history.canSendPeakNext());
  assertTrue(history.canSendNadirNext());
  assertEqual(80, (int)history.peakSend->first().rssi);
  assertEqual(time(1)-1, (int)history.peakSend->first().duration);

  history.nadirSend->removeFirst();

  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(20, (int)history.nadirSend->first().rssi);
  assertEqual(time(1)-1, (int)history.nadirSend->first().duration);

  history.peakSend->removeFirst();

  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertFalse(history.canSendPeakNext());
  assertTrue(history.canSendNadirNext());
  assertEqual(60, (int)history.peakSend->first().rssi);

  history.nadirSend->removeFirst();

  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertTrue(history.canSendPeakNext());
  assertFalse(history.canSendNadirNext());
  assertEqual(40, (int)history.nadirSend->first().rssi);
}

unittest_main()
