#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "util.h"
#include "../util/multi-sendbuffer.h"

MultiSendBuffer<Extremum,1> testPeakBuffer1;
MultiSendBuffer<Extremum,1> testNadirBuffer1;

/**
 * Tests history buffer.
 */
unittest(historyBuffer_multi1_withoutReads) {
  GodmodeState* nano = GODMODE();
  nano->reset();

  RssiNode::multiRssiNodeCount = 1;
  RssiNode *rssiNodePtr = &(RssiNode::rssiNodeArray[0]);
  rssiNodePtr->rssiSetSendBuffers(&testPeakBuffer1, &testNadirBuffer1);
  rssiNodePtr->rssiSetFilter(&testFilter);
  rssiNodePtr->rssiInit();
  rssiNodePtr->rssiStateReset();

  rssiNodePtr->setActivatedFlag(true);

  // prime the state with some background signal
  sendSignal(rssiNodePtr, nano, 60);
  sendSignal(rssiNodePtr, nano, 40);

  struct History & history = rssiNodePtr->getHistory();

  // small extremum peak
  sendSignal(rssiNodePtr, nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(60, (int)history.peakSend->first().rssi);
  // small extremum nadir
  sendSignal(rssiNodePtr, nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(40, (int)history.nadirSend->first().rssi);

  // large extremum peak
  sendSignal(rssiNodePtr, nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(60, (int)history.peakSend->first().rssi);
  // large extremum nadir
  sendSignal(rssiNodePtr, nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(40, (int)history.nadirSend->first().rssi);

  // large extremum peak
  sendSignal(rssiNodePtr, nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(80, (int)history.peakSend->first().rssi);
  assertEqual(time(1)-1, (int)history.peakSend->first().duration);
  // large extremum nadir
  sendSignal(rssiNodePtr, nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(20, (int)history.nadirSend->first().rssi);
  assertEqual(time(1)-1, (int)history.nadirSend->first().duration);

  // small extremum peak
  sendSignal(rssiNodePtr, nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(80, (int)history.peakSend->first().rssi);
  // overwrite
  assertEqual(time(1)-1, (int)history.peakSend->first().duration);
  // small extremum nadir
  sendSignal(rssiNodePtr, nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(20, (int)history.nadirSend->first().rssi);
  // overwrite
  assertEqual(time(1)-1, (int)history.nadirSend->first().duration);

  sendSignal(rssiNodePtr, nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  // overwrite
  assertEqual(60, (int)history.peakSend->first().rssi);
  sendSignal(rssiNodePtr, nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  // overwrite
  assertEqual(40, (int)history.nadirSend->first().rssi);
}

/**
 * Tests history buffer.
 */
unittest(historyBuffer_multi1_withReads) {
  GodmodeState* nano = GODMODE();
  nano->reset();

  RssiNode::multiRssiNodeCount = 1;
  RssiNode *rssiNodePtr = &(RssiNode::rssiNodeArray[0]);
  rssiNodePtr->rssiSetSendBuffers(&testPeakBuffer1, &testNadirBuffer1);
  rssiNodePtr->rssiInit();
  rssiNodePtr->rssiStateReset();

  rssiNodePtr->setActivatedFlag(true);

  // prime the state with some background signal
  sendSignal(rssiNodePtr, nano, 60);
  sendSignal(rssiNodePtr, nano, 40);

  struct History & history = rssiNodePtr->getHistory();

  // small extremum peak
  sendSignal(rssiNodePtr, nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(60, (int)history.peakSend->first().rssi);
  // small extremum nadir
  sendSignal(rssiNodePtr, nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(40, (int)history.nadirSend->first().rssi);

  // large extremum peak
  sendSignal(rssiNodePtr, nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(60, (int)history.peakSend->first().rssi);
  // large extremum nadir
  sendSignal(rssiNodePtr, nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(40, (int)history.nadirSend->first().rssi);

  // large extremum peak
  sendSignal(rssiNodePtr, nano, 80);
  assertEqual(80, (int)history.peak.rssi);
  assertEqual(80, (int)history.peakSend->first().rssi);
  assertEqual(time(1)-1, (int)history.peakSend->first().duration);
  // large extremum nadir
  sendSignal(rssiNodePtr, nano, 20);
  assertEqual(20, (int)history.nadir.rssi);
  assertEqual(20, (int)history.nadirSend->first().rssi);
  assertEqual(time(1)-1, (int)history.nadirSend->first().duration);

  history.peakSend->removeFirst();

  // small extremum peak
  sendSignal(rssiNodePtr, nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(80, (int)history.peakSend->first().rssi);
  assertEqual(time(1)-1, (int)history.peakSend->first().duration);

  history.nadirSend->removeFirst();

  // small extremum nadir
  sendSignal(rssiNodePtr, nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(20, (int)history.nadirSend->first().rssi);
  assertEqual(time(1)-1, (int)history.nadirSend->first().duration);

  history.peakSend->removeFirst();

  sendSignal(rssiNodePtr, nano, 60);
  assertEqual(60, (int)history.peak.rssi);
  assertEqual(60, (int)history.peakSend->first().rssi);

  history.nadirSend->removeFirst();

  sendSignal(rssiNodePtr, nano, 40);
  assertEqual(40, (int)history.nadir.rssi);
  assertEqual(40, (int)history.nadirSend->first().rssi);
}

unittest_main()
