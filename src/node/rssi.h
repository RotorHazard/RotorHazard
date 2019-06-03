#ifndef rssi_h
#define rssi_h

#include "rhtypes.h"

#define MAX_RSSI 0xFF
#define SmoothingSamples 255
#define SmoothingTimestampSize 127 // half median window, rounded up

struct Settings
{
    uint16_t volatile vtxFreq = 5800;
    // lap pass begins when RSSI is at or above this level
    rssi_t volatile enterAtLevel = 96;
    // lap pass ends when RSSI goes below this level
    rssi_t volatile exitAtLevel = 80;
};

struct State
{
    bool volatile crossing = false; // True when the quad is going through the gate
    rssi_t volatile rssiSmoothed = 0; // Smoothed rssi value
    rssi_t volatile lastRssiSmoothed = 0;
    mtime_t volatile rssiTimestamp = 0; // timestamp of the smoothed value

    rssi_t volatile passRssiPeakRaw = 0; // peak raw rssi seen during current pass
    rssi_t volatile passRssiPeak = 0; // peak smoothed rssi seen during current pass
    mtime_t volatile passRssiPeakRawTime = 0; // time of the first peak raw rssi for the current pass
    mtime_t volatile passRssiPeakRawLastTime = 0; // time of the last peak raw rssi for the current pass
    rssi_t volatile passRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since end of last pass

    rssi_t volatile nodeRssiPeak = 0; // peak smoothed rssi seen since the node frequency was set
    rssi_t volatile nodeRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since the node frequency was set

    bool volatile rxFreqSetFlag = false; // Set true after initial WRITE_FREQUENCY command received

    // variables to track the loop time
    utime_t volatile loopTimeMicros = 0;
    utime_t volatile lastloopMicros = 0;
};

struct History
{
    rssi_t volatile peakRssi;
    mtime_t volatile peakFirstTime;
    mtime_t volatile peakLastTime;
    bool volatile peakSend;
    rssi_t volatile peakSendRssi;
    mtime_t volatile peakSendFirstTime;
    mtime_t volatile peakSendLastTime;

    rssi_t volatile nadirRssi;
    mtime_t volatile nadirTime;
    bool volatile nadirSend;
    rssi_t volatile nadirSendRssi;
    mtime_t volatile nadirSendTime;

    int8_t volatile rssiChange; // >0 for raising, <0 for falling
};

struct LastPass
{
    rssi_t volatile rssiPeak;
    mtime_t volatile timestamp;
    rssi_t volatile rssiNadir;
    uint8_t volatile lap;
};

extern struct Settings settings;
extern struct State state;
extern struct History history;
extern struct LastPass lastPass;

void rssiInit();
bool rssiStateValid();
/**
 * Restarts rssi peak tracking for node.
 */
void rssiStateReset();
void rssiProcess(rssi_t rssi, mtime_t millis);
void rssiEndCrossing();

#endif
