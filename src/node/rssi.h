#ifndef rssi_h
#define rssi_h

#include "config.h"
#include "util/filter.h"
#include "util/median-filter.h"
#include "util/lowpass20hz-filter.h"
#include "util/lowpass50hz-filter.h"
#include "util/lowpass100hz-filter.h"
#include "util/no-filter.h"
#include "util/sendbuffer.h"
#include "util/single-sendbuffer.h"
#include "util/multi-sendbuffer.h"

#define MAX_DURATION 0xFFFF

#define FILTER_NONE NoFilter<rssi_t>
#define FILTER_MEDIAN MedianFilter<rssi_t, SmoothingSamples, 0>
#define FILTER_100 LowPassFilter100Hz
#define FILTER_50 LowPassFilter50Hz
#define FILTER_20 LowPassFilter20Hz

//select the filter to use here
#define FILTER_IMPL FILTER_MEDIAN

#define PEAK_SENDBUFFER_SINGLE SinglePeakSendBuffer
#define PEAK_SENDBUFFER_MULTI MultiSendBuffer<Extremum,10>
#define NADIR_SENDBUFFER_SINGLE SingleNadirSendBuffer
#define NADIR_SENDBUFFER_MULTI MultiSendBuffer<Extremum,10>

//select the send buffer to use here
#define PEAK_SENDBUFFER_IMPL PEAK_SENDBUFFER_SINGLE
#define NADIR_SENDBUFFER_IMPL NADIR_SENDBUFFER_SINGLE

struct Settings
{
    uint16_t volatile vtxFreq = 5800;
    // lap pass begins when RSSI is at or above this level
    rssi_t volatile enterAtLevel = 96;
    // lap pass ends when RSSI goes below this level
    rssi_t volatile exitAtLevel = 80;
};

class State
{
public:
    // variables to track the loop time
    utime_t volatile loopTimeMicros = 0;
    utime_t lastloopMicros = 0;

    bool volatile crossing = false; // True when the quad is going through the gate
    rssi_t volatile rssi = 0; // Smoothed rssi value
    rssi_t lastRssi = 0;
    mtime_t rssiTimestamp = 0; // timestamp of the smoothed value

    Extremum passPeak = {0, 0, 0}; // peak seen during current pass - only valid if pass.rssi != 0
    rssi_t passRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since end of last pass

    rssi_t volatile nodeRssiPeak = 0; // peak smoothed rssi seen since the node frequency was set
    rssi_t volatile nodeRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since the node frequency was set

    bool volatile activatedFlag = false; // Set true after initial WRITE_FREQUENCY command received

    /**
     * Returns the RSSI change since the last reading.
     */
    inline int readRssiFromFilter(Filter<rssi_t>* f);
    inline void updateLoopTime(utime_t loopMicros);
    inline void resetPass();
    inline void reset();
};

class History
{
private:
    PEAK_SENDBUFFER_IMPL defaultPeakSendBuffer;
    NADIR_SENDBUFFER_IMPL defaultNadirSendBuffer;

    bool hasPendingPeak = false;
    bool hasPendingNadir = false;

    void bufferPeak(bool force);
    void bufferNadir(bool force);

#ifdef __TEST__
public:
#endif
    int8_t prevRssiChange = 0; // >0 for raising, <0 for falling
public:
    Extremum peak = {0, 0, 0};
    Extremum nadir = {MAX_RSSI, 0, 0};
    SendBuffer<Extremum> *peakSend = nullptr;
    SendBuffer<Extremum> *nadirSend = nullptr;

    History();
    void setSendBuffers(SendBuffer<Extremum> *peak, SendBuffer<Extremum> *nadir);
    inline void startNewPeak(rssi_t rssi, mtime_t ts);
    inline void startNewNadir(rssi_t rssi, mtime_t ts);
    void bufferPeak() {bufferPeak(false);};
    void bufferNadir() {bufferNadir(false);};
    inline void recordRssiChange(int delta);
    bool canSendPeakNext();
    inline void checkForPeak();
    bool canSendNadirNext();
    inline void checkForNadir();
    inline void reset();
};

struct LastPass
{
    rssi_t volatile rssiPeak = 0;
    mtime_t volatile timestamp = 0;
    rssi_t volatile rssiNadir = MAX_RSSI;
    uint8_t volatile lap = 0;
};

class RssiNode
{
private:
    FILTER_IMPL defaultFilter;

    struct Settings settings;
    State state;
    History history;
    struct LastPass lastPass;

    Filter<rssi_t> *filter;

public:
    RssiNode();
    void setFilter(Filter<rssi_t> *f);
    void start();
    bool isStateValid();
    /**
     * Restarts rssi peak tracking for node.
     */
    void resetState();
    bool process(rssi_t rssi, mtime_t millis);
    void endCrossing();

    struct Settings& getSettings() { return settings; };
    struct State& getState() { return state; };
    struct History& getHistory() { return history; };
    struct LastPass& getLastPass() { return lastPass; };
};
#endif
