#ifndef TEST_UTIL_H
#define TEST_UTIL_H

#include "../RssiNode.h"
#include "../util/median-filter.h"

MedianFilter<rssi_t, SmoothingSamples, 0> testFilter;

#define milliTick(nano) (nano->micros += 1000)

const static int N_2 = testFilter.getSampleCapacity()/2+1;
const static int N_TS = testFilter.getTimestampCapacity();

void sendSignal(RssiNode *rssiNodePtr, GodmodeState* nano, int rssi) {
  for(int t=0; t<N_2; t++) {
    rssiNodePtr->rssiProcessValue(millis(), rssi);
    milliTick(nano);
  }
}

mtime_t timestamp(int sendCount) {
  return sendCount*N_2 - N_TS;
}

mtime_t time(int sendCount) {
  return sendCount*N_2;
}

#endif  //TEST_UTIL_H
