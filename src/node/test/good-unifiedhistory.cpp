#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssi.h"
#include "util.h"
#include "../util/unified-sendbuffer.h"

unittest(historyBuffer_unified_preserves_order) {
    UnifiedSendBuffer<Extremum,2> buf;
    assertEqual(NONE, buf.nextType());
    Extremum e1 = {30,0,0};
    buf.addPeak(e1);
    Extremum e3 = {60,0,0};
    buf.addPeak(e3);
    assertEqual(1, buf.size());
    assertEqual(PEAK, buf.typeAt(0));
    assertEqual(PEAK, buf.nextType());
    Extremum e2 = {40,0,0};
    buf.addNadir(e2);
    assertEqual(2, buf.size());
    assertEqual(PEAK, buf.typeAt(0));
    assertEqual(NADIR, buf.typeAt(1));
    assertEqual(PEAK, buf.nextType());
    Extremum next = buf.nextPeak();
    assertEqual(e1.rssi, next.rssi);
    next = buf.nextNadir();
    assertEqual(e2.rssi, next.rssi);
    next = buf.popNext();
    assertEqual(e1.rssi, next.rssi);
    assertEqual(2, buf.size());
    assertEqual(PEAK, buf.typeAt(0));
    assertEqual(NADIR, buf.typeAt(1));
    assertEqual(1, buf.remainingToSend());
    assertEqual(NADIR, buf.nextType());
    buf.addPeak(e3);
    assertEqual(2, buf.size());
    assertEqual(NADIR, buf.typeAt(0));
    assertEqual(PEAK, buf.typeAt(1));
    assertEqual(2, buf.remainingToSend());
    assertEqual(NADIR, buf.nextType());
    next = buf.nextNadir();
    assertEqual(e2.rssi, next.rssi);
    next = buf.nextPeak();
    assertEqual(e3.rssi, next.rssi);
}

/**
 * Tests history buffer.
 */
unittest(historyBuffer_unified1_withoutReads) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  rssiNode.setFilter(&testFilter);
  State& state = rssiNode.getState();
  LastPass& lastPass = rssiNode.getLastPass();
  History& history = rssiNode.getHistory();
  UnifiedSendBuffer<Extremum,2> testBuffer;
  history.setSendBuffer(&testBuffer);
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
  assertEqual(1, history.sendBuffer->size());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(2)-1, (int)history.sendBuffer->nextNadir().duration);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(2, history.sendBuffer->size());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(40, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(40, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
}

/**
 * Tests history buffer.
 */
unittest(historyBuffer_unified1_withReads) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  State& state = rssiNode.getState();
  LastPass& lastPass = rssiNode.getLastPass();
  History& history = rssiNode.getHistory();
  UnifiedSendBuffer<Extremum,2> testBuffer;
  history.setSendBuffer(&testBuffer);
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
  assertEqual(1, history.sendBuffer->size());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(2)-1, (int)history.sendBuffer->nextNadir().duration);
  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(2, history.sendBuffer->size());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(40, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  // large extremum peak
  sendSignal(nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  // large extremum nadir
  sendSignal(nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  assertEqual(2, testBuffer.remainingToSend());
  history.popNextToSend();
  assertEqual(1, testBuffer.remainingToSend());

  // small extremum peak
  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);

  assertEqual(2, testBuffer.remainingToSend());
  history.popNextToSend();
  assertEqual(1, testBuffer.remainingToSend());

  // small extremum nadir
  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  assertEqual(2, testBuffer.remainingToSend());
  history.popNextToSend();
  assertEqual(1, testBuffer.remainingToSend());

  sendSignal(nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(40, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);

  assertEqual(2, testBuffer.remainingToSend());
  history.popNextToSend();
  assertEqual(1, testBuffer.remainingToSend());

  sendSignal(nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
}

unittest_main()
