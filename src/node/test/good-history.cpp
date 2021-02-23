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
  assertEqual(NONE, history.nextToSendType());

  rssiNode.active = true;

  // prime the state with some background signal
  sendSignal(nano, 60);
  sendSignal(nano, 30);
  sendSignal(nano, 30);

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(2)-1, (int)history.sendBuffer->nextNadir().duration);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(680, (int)history.sendBuffer->nextPeak().firstTime);
  // couldn't merge with previous peak due to trailing nadir
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(808, (int)history.sendBuffer->nextNadir().firstTime);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(680, (int)history.sendBuffer->nextPeak().firstTime);
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(808, (int)history.sendBuffer->nextNadir().firstTime);
  // merges with previous nadir
  assertEqual(time(3)-1, (int)history.sendBuffer->nextNadir().duration);

  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  // current large peak in peakSend is kept over new smaller peak
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  // current large nadir in nadirSend is kept over new smaller nadir
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
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
  assertEqual(NONE, history.nextToSendType());

  rssiNode.active = true;

  // prime the state with some background signal
  sendSignal(nano, 60);
  sendSignal(nano, 30);
  sendSignal(nano, 30);

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(2)-1, (int)history.sendBuffer->nextNadir().duration);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);

  assertEqual(1, peakBuffer.size());
  assertEqual(1, nadirBuffer.size());
  history.popNextToSend();
  assertEqual(0, peakBuffer.size());
  assertEqual(1, nadirBuffer.size());

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  assertEqual(1, peakBuffer.size());
  assertEqual(1, nadirBuffer.size());
  history.popNextToSend();
  assertEqual(1, peakBuffer.size());
  assertEqual(0, nadirBuffer.size());

  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);

  assertEqual(1, peakBuffer.size());
  assertEqual(1, nadirBuffer.size());
  history.popNextToSend();
  assertEqual(0, peakBuffer.size());
  assertEqual(1, nadirBuffer.size());

  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);

  assertEqual(1, peakBuffer.size());
  assertEqual(1, nadirBuffer.size());
  history.popNextToSend();
  assertEqual(1, peakBuffer.size());
  assertEqual(0, nadirBuffer.size());

  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(40, (int)history.sendBuffer->nextNadir().rssi);
}

unittest_main()
