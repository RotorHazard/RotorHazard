#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssi.h"
#include "util.h"

SENDBUFFER phSendBuffer;

unittest(phCrossing) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  phSendBuffer.clear();
  RssiNode rssiNode;
  configureTestRssiNode(rssiNode);
  Settings& settings = rssiNode.getSettings();
  settings.usePh = true;
  settings.enterAtLevel = settings.exitAtLevel = 10;
  State& state = rssiNode.getState();
  LastPass& lastPass = rssiNode.getLastPass();
  History& history = rssiNode.getHistory();
  history.setSendBuffer(&phSendBuffer);
  rssiNode.start(millis(), micros());

  // prime the state with some background signal
  sendSignal(nano, rssiNode, 50);
  assertFalse(rssiNode.isStateValid());
  // more signal needed
  sendSignal(nano, rssiNode, 50);
  sendSignal(nano, rssiNode, 50);
  assertEqual(3*N_2*1000-1000, state.lastloopMicros);
  assertTrue(rssiNode.isStateValid());
  assertEqual(50, (int)state.rssi);
  assertEqual(timestamp(3), (int)state.rssiTimestamp);
  assertEqual(50, (int)state.lastRssi);
  assertEqual(50, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);

  // enter
  sendSignal(nano, rssiNode, 130);
  assertEqual(130, (int)state.rssi);
  assertEqual(timestamp(4), (int)state.rssiTimestamp);
  assertEqual(50, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertTrue(state.crossing);

  assertEqual(130, (int)state.passPeak.rssi);
  assertEqual(timestamp(4), (int)state.passPeak.firstTime);
  assertEqual(0, (int)state.passPeak.duration);
  assertEqual(50, (int)state.passRssiNadir);

  assertEqual(80, (int)history.prevRssiChange);
  assertEqual(130, (int)history.peak.rssi); // first upward trend
  assertEqual(timestamp(4), (int)history.peak.firstTime);
  assertEqual(0, (int)history.peak.duration);
  assertEqual(50, history.nadir.rssi); // starting nadir
  assertEqual(timestamp(4)-1, (int)history.nadir.firstTime);

  assertEqual(NADIR, history.nextToSendType());
  history.popNextToSend();

  // exit
  sendSignal(nano, rssiNode, 70);
  assertEqual(70, (int)state.rssi);
  assertEqual(timestamp(5), (int)state.rssiTimestamp);
  assertEqual(130, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertFalse(state.crossing);

  assertFalse(isPeakValid(state.passPeak)); // crossing/pass finished
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(-60, (int)history.prevRssiChange);
  assertEqual(130, (int)history.peak.rssi);
  assertEqual(timestamp(4), (int)history.peak.firstTime);
  assertEqual(time(1)-1, (int)history.peak.duration);
  assertEqual(70, (int)history.nadir.rssi); // first downward trend
  assertEqual(timestamp(5), (int)history.nadir.firstTime);
  assertEqual(0, (int)history.nadir.duration);

  assertEqual(130, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(timestamp(4), (int)history.sendBuffer->nextPeak().firstTime);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
  assertEqual(PEAK, history.nextToSendType());

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(4)+timestamp(5)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);

  // small rise
  sendSignal(nano, rssiNode, 75);
  assertEqual(75, (int)state.rssi);
  assertEqual(timestamp(6), (int)state.rssiTimestamp);
  assertEqual(70, (int)state.lastRssi);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertFalse(state.crossing);

  assertEqual(0, (int)state.passPeak.rssi);
  assertEqual(70, (int)state.passRssiNadir);

  assertEqual(5, (int)history.prevRssiChange);
  assertEqual(75, (int)history.peak.rssi);
  assertEqual(timestamp(6), (int)history.peak.firstTime);
  assertEqual(0, (int)history.peak.duration);
  assertEqual(70, (int)history.nadir.rssi);
  assertEqual(timestamp(5), (int)history.nadir.firstTime);
  assertEqual(time(1)-1, (int)history.nadir.duration);

  assertEqual(130, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(timestamp(4), (int)history.sendBuffer->nextPeak().firstTime);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
  history.popNextToSend();
  assertEqual(70, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(timestamp(5), (int)history.sendBuffer->nextNadir().firstTime);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(4)+timestamp(5)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);

  // small fall
  sendSignal(nano, rssiNode, 60);

  assertEqual(75, (int)history.sendBuffer->nextPeak().rssi);
  assertEqual(timestamp(6), (int)history.sendBuffer->nextPeak().firstTime);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextPeak().duration);
  assertEqual(70, (int)history.sendBuffer->nextNadir().rssi);
  assertEqual(timestamp(5), (int)history.sendBuffer->nextNadir().firstTime);
  assertEqual(time(1)-1, (int)history.sendBuffer->nextNadir().duration);
  history.popNextToSend();
}

unittest(preparePhData)
{
    phSendBuffer.clear();
    RssiNode rssiNode;
    configureTestRssiNode(rssiNode);
    History& history = rssiNode.getHistory();
    history.setSendBuffer(&phSendBuffer);
    Extremum e1 = {50,0,0};
    phSendBuffer.addPeak(e1);
    Extremum e2 = {20,0,0};
    phSendBuffer.addNadir(e2);
    Extremum e3 = {60,0,0};
    phSendBuffer.addPeak(e3);
    rssiNode.preparePhData(30);
    assertEqual(50, (int)rssiNode.phData[0]);
    assertEqual(20, (int)rssiNode.phData[1]);
    assertEqual(60, (int)rssiNode.phData[2]);
    assertEqual(30, (int)rssiNode.phData[3]);
    assertEqual(1, (int)rssiNode.phSortedIdxs[0]);
    assertEqual(3, (int)rssiNode.phSortedIdxs[1]);
    assertEqual(0, (int)rssiNode.phSortedIdxs[2]);
    assertEqual(2, (int)rssiNode.phSortedIdxs[3]);
}

unittest_main()
