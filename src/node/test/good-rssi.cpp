#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssi.h"

#define N_2 (SmoothingSamples/2+1)
#define milliTick(nano) (nano->micros += 1000)
#define timestamp(sendCount) ((sendCount)*N_2-SmoothingTimestampSize)

void sendSignal(GodmodeState* nano, int rssi) {
  for(int t=0; t<N_2; t++) {
    rssiProcess(rssi, millis());
    milliTick(nano);
  }
}

unittest(crossing) {
  GodmodeState* nano = GODMODE();
  nano->reset();
  rssiInit();

  state.rxFreqSetFlag = true;

  // prime the state with some background signal
  sendSignal(nano, 50);
  assertEqual(false, rssiStateValid());
  // more signal needed
  sendSignal(nano, 50);
  assertEqual(2*N_2*1000-1000, state.lastloopMicros);
  assertEqual(true, rssiStateValid());
  assertEqual(50, (int)state.rssiSmoothed);
  assertEqual(timestamp(2), (int)state.rssiTimestamp);
  assertEqual(50, (int)state.lastRssiSmoothed);
  assertEqual(50, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);

  // enter
  sendSignal(nano, 130);
  assertEqual(130, (int)state.rssiSmoothed);
  assertEqual(timestamp(3), (int)state.rssiTimestamp);
  assertEqual(50, (int)state.lastRssiSmoothed);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertEqual(80, history.rssiChange);
  assertEqual(true, state.crossing);

  assertEqual(130, (int)state.passRssiPeak);
  assertEqual(130, (int)state.passRssiPeakRaw);
  assertEqual(timestamp(3), (int)state.passRssiPeakRawTime);
  assertEqual(timestamp(3), (int)state.passRssiPeakRawLastTime);
  assertEqual(130, (int)history.peakRssi); // first upward trend
  assertEqual(0, (int)history.nadirRssi); // no downward trend yet
  assertEqual(timestamp(3), (int)history.peakFirstTime);
  assertEqual(timestamp(3), (int)history.peakLastTime);

  assertEqual(0, (int)history.peakSendRssi);
  assertEqual(0, (int)history.peakSendFirstTime);
  assertEqual(0, (int)history.peakSendLastTime);
  assertEqual(0, (int)history.nadirTime);
  assertEqual(0, (int)history.nadirSendRssi);
  assertEqual(0, (int)history.nadirSendTime);

  // exit
  sendSignal(nano, 70);
  assertEqual(70, (int)state.rssiSmoothed);
  assertEqual(timestamp(4), (int)state.rssiTimestamp);
  assertEqual(130, (int)state.lastRssiSmoothed);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertEqual(-60, history.rssiChange);
  assertEqual(false, state.crossing);

  assertEqual(0, (int)state.passRssiPeak); // crossing/pass finished
  assertEqual(0, (int)state.passRssiPeakRaw); // crossing/pass finished
  assertEqual(timestamp(3), (int)state.passRssiPeakRawTime);
  assertEqual(timestamp(4)-1, (int)state.passRssiPeakRawLastTime);
  assertEqual(130, (int)history.peakRssi);
  assertEqual(70, (int)history.nadirRssi); // first downward trend

  assertEqual(130, (int)history.peakSendRssi);
  assertEqual(timestamp(3), (int)history.peakSendFirstTime);
  assertEqual(timestamp(4)-1, (int)history.peakSendLastTime);
  assertEqual(timestamp(4), (int)history.nadirTime);
  assertEqual(0, (int)history.nadirSendRssi);
  assertEqual(0, (int)history.nadirSendTime);

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual(320, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);

  // small rise
  sendSignal(nano, 75);
  assertEqual(75, (int)state.rssiSmoothed);
  assertEqual(timestamp(5), (int)state.rssiTimestamp);
  assertEqual(70, (int)state.lastRssiSmoothed);
  assertEqual(130, (int)state.nodeRssiPeak);
  assertEqual(50, (int)state.nodeRssiNadir);
  assertEqual(5, history.rssiChange);
  assertEqual(false, state.crossing);

  assertEqual(0, (int)state.passRssiPeak);
  assertEqual(75, (int)state.passRssiPeakRaw);
  assertEqual(timestamp(5), (int)state.passRssiPeakRawTime);
  assertEqual(timestamp(5), (int)state.passRssiPeakRawLastTime);
  assertEqual(75, (int)history.peakRssi);
  assertEqual(70, (int)history.nadirRssi);

  assertEqual(130, (int)history.peakSendRssi);
  assertEqual(timestamp(3), (int)history.peakSendFirstTime);
  assertEqual(timestamp(4)-1, (int)history.peakSendLastTime);
  assertEqual(timestamp(4), (int)history.nadirTime);
  assertEqual(70, (int)history.nadirSendRssi);
  assertEqual(timestamp(4), (int)history.nadirSendTime);

  assertEqual(130, (int)lastPass.rssiPeak);
  assertEqual(50, (int)lastPass.rssiNadir);
  assertEqual((timestamp(3)+timestamp(4)-1)/2, (int)lastPass.timestamp);
  assertEqual(1, (int)lastPass.lap);
}

unittest_main()
