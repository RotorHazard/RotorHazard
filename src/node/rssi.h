#ifndef rssi_h
#define rssi_h

#include "rhtypes.h"

#define MAX_RSSI 0xFF
#define SmoothingSamples 255
#define SmoothingTimestampSize 127 // half median window, rounded up
#define isPeakValid(x) ((x) != 0)
#define isNadirValid(x) ((x) != MAX_RSSI)

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
    rssi_t volatile rssi = 0; // Smoothed rssi value
    rssi_t lastRssi = 0;
    mtime_t rssiTimestamp = 0; // timestamp of the smoothed value

    rssi_t passRssiPeak = 0; // peak smoothed rssi seen during current pass
    mtime_t passRssiPeakFirstTime = 0; // time of the first peak rssi for the current pass - only valid if passRssiPeak != 0
    mtime_t passRssiPeakLastTime = 0; // time of the last peak rssi for the current pass - only valid if passRssiPeak != 0
    rssi_t passRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since end of last pass

    rssi_t volatile nodeRssiPeak = 0; // peak smoothed rssi seen since the node frequency was set
    rssi_t volatile nodeRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since the node frequency was set

    bool volatile rxFreqSetFlag = false; // Set true after initial WRITE_FREQUENCY command received

    // variables to track the loop time
    utime_t volatile loopTimeMicros = 0;
    utime_t lastloopMicros = 0;
};

struct History
{
    rssi_t volatile peakRssi;
    mtime_t volatile peakFirstTime;
    mtime_t volatile peakLastTime;
    bool volatile hasPendingPeak;
    rssi_t volatile peakSendRssi = 0;
    mtime_t volatile peakSendFirstTime; // only valid if peakSendRssi != 0
    mtime_t volatile peakSendLastTime; // only valid if peakSendRssi != 0

    rssi_t volatile nadirRssi;
    mtime_t volatile nadirTime;
    bool volatile hasPendingNadir;
    rssi_t volatile nadirSendRssi = MAX_RSSI;
    mtime_t volatile nadirSendTime; // only valid if nadirSendRssi != MAX_RSSI

    int8_t rssiChange; // >0 for raising, <0 for falling
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
