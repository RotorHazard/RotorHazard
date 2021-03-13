#include "../rssirx.h"

MedianFilter<rssi_t, SmoothingSamples, 0> testFilter;

#define milliTick(nano) (nano->micros += 1000)

const static int N_2 = testFilter.getSampleCapacity()/2+1;
const static int N_TS = testFilter.getTimestampCapacity();

void configureTestRssiNode(RssiNode& rssiNode) {
    testFilter.reset();
    rssiNode.setFilter(&testFilter);
}

void sendSignal(GodmodeState* nano, RssiNode& rssiNode, int rssi) {
    for(int t=0; t<N_2; t++) {
        rssiNode.process(rssi, millis());
        rssiNode.getState().updateLoopTime(micros());
        milliTick(nano);
    }
}

void readRssi(GodmodeState* nano, int rssi) {
    nano->analogPin[0] = rssi<<1;
    for(int t=0; t<N_2; t++) {
      rssiRxs.readRssi(millis(), micros());
      milliTick(nano);
    }
}

mtime_t timestamp(int sendCount) {
    return sendCount*N_2 - N_TS;
}

mtime_t time(int sendCount) {
    return sendCount*N_2;
}
