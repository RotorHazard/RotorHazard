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
  RssiNode rssiNode;
  configureTestRssiNode(rssiNode);
  State& state = rssiNode.getState();
  LastPass& lastPass = rssiNode.getLastPass();
  History& history = rssiNode.getHistory();
  UnifiedSendBuffer<Extremum,2> testBuffer;
  history.setSendBuffer(&testBuffer);
  rssiNode.start(millis(), micros());
  nano->micros += 40000; // settle time
  assertEqual(NONE, history.nextToSendType());

  // prime the state with some background signal
  sendSignal(nano, rssiNode, 60);
  sendSignal(nano, rssiNode, 30);
  sendSignal(nano, rssiNode, 30);

  // small extremum peak
  sendSignal(nano, rssiNode, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(1, history.sendBuffer->size());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(2)-1, (int)history.sendBuffer->nextNadir().duration);
  // small extremum nadir
  sendSignal(nano, rssiNode, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(2, history.sendBuffer->size());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  // large extremum peak
  sendSignal(nano, rssiNode, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(40, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  // large extremum nadir
  sendSignal(nano, rssiNode, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  // large extremum peak
  sendSignal(nano, rssiNode, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  // large extremum nadir
  sendSignal(nano, rssiNode, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  // small extremum peak
  sendSignal(nano, rssiNode, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  // small extremum nadir
  sendSignal(nano, rssiNode, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  sendSignal(nano, rssiNode, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(40, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  sendSignal(nano, rssiNode, 40);
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
  RssiNode rssiNode;
  configureTestRssiNode(rssiNode);
  State& state = rssiNode.getState();
  LastPass& lastPass = rssiNode.getLastPass();
  History& history = rssiNode.getHistory();
  UnifiedSendBuffer<Extremum,2> testBuffer;
  history.setSendBuffer(&testBuffer);
  rssiNode.start(millis(), micros());
  nano->micros += 40000; // settle time
  assertEqual(NONE, history.nextToSendType());

  // prime the state with some background signal
  sendSignal(nano, rssiNode, 60);
  sendSignal(nano, rssiNode, 30);
  sendSignal(nano, rssiNode, 30);

  // small extremum peak
  sendSignal(nano, rssiNode, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(1, history.sendBuffer->size());
  assertEqual(30, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(2)-1, (int)history.sendBuffer->nextNadir().duration);
  // small extremum nadir
  sendSignal(nano, rssiNode, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(2, history.sendBuffer->size());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  // large extremum peak
  sendSignal(nano, rssiNode, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(40, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  // large extremum nadir
  sendSignal(nano, rssiNode, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  // large extremum peak
  sendSignal(nano, rssiNode, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  // large extremum nadir
  sendSignal(nano, rssiNode, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(80, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  assertEqual(2, testBuffer.remainingToSend());
  history.popNextToSend();
  assertEqual(1, testBuffer.remainingToSend());

  // small extremum peak
  sendSignal(nano, rssiNode, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(20, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);

  assertEqual(2, testBuffer.remainingToSend());
  history.popNextToSend();
  assertEqual(1, testBuffer.remainingToSend());

  // small extremum nadir
  sendSignal(nano, rssiNode, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);

  assertEqual(2, testBuffer.remainingToSend());
  history.popNextToSend();
  assertEqual(1, testBuffer.remainingToSend());

  sendSignal(nano, rssiNode, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(PEAK, history.nextToSendType());
  assertEqual(40, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);

  assertEqual(2, testBuffer.remainingToSend());
  history.popNextToSend();
  assertEqual(1, testBuffer.remainingToSend());

  sendSignal(nano, rssiNode, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(NADIR, history.nextToSendType());
  assertEqual(60, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
}

unittest(historyBuffer_sorted) {
    SortedUnifiedSendBuffer<3> testBuffer;
    Extremum e1 = {80,0,0};
    testBuffer.addPeak(e1);
    Extremum e2 = {30,0,0};
    testBuffer.addNadir(e2);
    assertEqual(2, (int)testBuffer.size());
    e2 = testBuffer[testBuffer.sortedIdxs[0]];
    e1 = testBuffer[testBuffer.sortedIdxs[1]];
    assertEqual(30, (int)e2.rssi);
    assertEqual(80, (int)e1.rssi);

    Extremum e3 = {70,0,0};
    testBuffer.addPeak(e3);
    assertEqual(3, (int)testBuffer.size());
    e2 = testBuffer[testBuffer.sortedIdxs[0]];
    e3 = testBuffer[testBuffer.sortedIdxs[1]];
    e1 = testBuffer[testBuffer.sortedIdxs[2]];
    assertEqual(30, (int)e2.rssi);
    assertEqual(70, (int)e3.rssi);
    assertEqual(80, (int)e1.rssi);

    Extremum e4 = {20,0,0};
    testBuffer.addNadir(e4);
    assertEqual(3, (int)testBuffer.size());
    e4 = testBuffer[testBuffer.sortedIdxs[0]];
    e2 = testBuffer[testBuffer.sortedIdxs[1]];
    e3 = testBuffer[testBuffer.sortedIdxs[2]];
    assertEqual(20, (int)e4.rssi);
    assertEqual(30, (int)e2.rssi);
    assertEqual(70, (int)e3.rssi);

    testBuffer.removeLast();
    assertEqual(2, (int)testBuffer.size());
    e2 = testBuffer[testBuffer.sortedIdxs[0]];
    e3 = testBuffer[testBuffer.sortedIdxs[1]];
    assertEqual(30, (int)e2.rssi);
    assertEqual(70, (int)e3.rssi);

    testBuffer.removeLast();
    assertEqual(1, (int)testBuffer.size());
    e2 = testBuffer[testBuffer.sortedIdxs[0]];
    assertEqual(30, (int)e2.rssi);
}

unittest_main()
