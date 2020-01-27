#ifndef rssi_h
#define rssi_h

#include "rhtypes.h"

#define MAX_RSSI 0xFF
#define MAX_DURATION 0xFFFF
#define isPeakValid(x) ((x).rssi != 0)
#define isNadirValid(x) ((x).rssi != MAX_RSSI)
#define endTime(x) ((x).firstTime + (x).duration)

struct Settings
{
    uint16_t volatile vtxFreq = 5800;
    // lap pass begins when RSSI is at or above this level
    rssi_t volatile enterAtLevel = 96;
    // lap pass ends when RSSI goes below this level
    rssi_t volatile exitAtLevel = 80;
};

struct Extremum
{
  rssi_t volatile rssi;
  mtime_t volatile firstTime;
  uint16_t volatile duration;
};

struct State
{
    bool volatile crossing = false; // True when the quad is going through the gate
    rssi_t volatile rssi = 0; // Smoothed rssi value
    rssi_t lastRssi = 0;
    mtime_t rssiTimestamp = 0; // timestamp of the smoothed value

    Extremum passPeak = {0, 0, 0}; // peak seen during current pass - only valid if pass.rssi != 0
    rssi_t passRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since end of last pass

    rssi_t volatile nodeRssiPeak = 0; // peak smoothed rssi seen since the node frequency was set
    rssi_t volatile nodeRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since the node frequency was set

    bool volatile activatedFlag = false; // Set true after initial WRITE_FREQUENCY command received

    // variables to track the loop time
    utime_t volatile loopTimeMicros = 0;
    utime_t lastloopMicros = 0;
};

struct History
{
    Extremum peak = {0, 0, 0};
    bool volatile hasPendingPeak = false;
    Extremum peakSend = {0, 0, 0}; // only valid if peakSend.rssi != 0

    Extremum nadir = {MAX_RSSI, 0, 0};
    bool volatile hasPendingNadir = false;
    Extremum nadirSend = {MAX_RSSI, 0, 0}; // only valid if nadirSend.rssi != MAX_RSSI

    int8_t rssiChange = 0; // >0 for raising, <0 for falling
};

struct LastPass
{
    rssi_t volatile rssiPeak = 0;
    mtime_t volatile timestamp = 0;
    rssi_t volatile rssiNadir = MAX_RSSI;
    uint8_t volatile lap = 0;
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
bool rssiProcess(rssi_t rssi, mtime_t millis);
void rssiEndCrossing();

#endif
