#ifndef rssi_h
#define rssi_h

#include "config.h"
#include "util/persistent-homology.h"
#include "util/filter.h"
#include "util/median-filter.h"
#include "util/lowpass15hz-filter.h"
#include "util/lowpass20hz-filter.h"
#include "util/lowpass50hz-filter.h"
#include "util/lowpass100hz-filter.h"
#include "util/composite-filter.h"
#include "util/no-filter.h"

#include "util/sendbuffer.h"
#include "util/single-sendbuffer.h"
#include "util/multi-sendbuffer.h"
#include "util/unified-sendbuffer.h"

#define MAX_DURATION 0xFFFF
#define toDuration(ms) uint16_t(min(uint32_t(ms), uint32_t(MAX_DURATION)))

#define HISTORY_SIZE 20
#define RSSI_HISTORY_SIZE 800 // NB: need to leave about a 100 bytes free RAM

#define USE_UNIFIED_SENDBUFFER
#ifdef __TEST__
#undef USE_UNIFIED_SENDBUFFER
#endif

#define SENDBUFFER UnifiedSendBuffer<Extremum,HISTORY_SIZE>

#define PEAK_SENDBUFFER_SINGLE SinglePeakSendBuffer
#define PEAK_SENDBUFFER_MULTI MultiPeakSendBuffer<HISTORY_SIZE/2>
#define NADIR_SENDBUFFER_SINGLE SingleNadirSendBuffer
#define NADIR_SENDBUFFER_MULTI MultiNadirSendBuffer<HISTORY_SIZE/2>

//select the send buffer to use here
#define PEAK_SENDBUFFER_IMPL PEAK_SENDBUFFER_MULTI
#define NADIR_SENDBUFFER_IMPL NADIR_SENDBUFFER_MULTI

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
    mtime_t rssiTimestamp = 0; // timestamp of the smoothed value
    rssi_t lastRssi = 0;
#ifdef RSSI_HISTORY
    CircularBuffer<rssi_t,RSSI_HISTORY_SIZE> rssiHistory;
    bool volatile rssiHistoryComplete = false;
#endif

    Extremum passPeak = {0, 0, 0}; // peak seen during current pass - only valid if pass.rssi != 0
    rssi_t passRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since end of last pass

    rssi_t volatile nodeRssiPeak = 0; // peak smoothed rssi seen since the node frequency was set
    rssi_t volatile nodeRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since the node frequency was set

    /**
     * Returns the RSSI change since the last reading.
     */
    inline int readRssiFromFilter(Filter<rssi_t>* f);
    inline void updateRssiStats();
    inline void updateLoopTime(utime_t loopMicros);
    inline void resetPass();
    inline void reset();
};

class History
{
#if defined(USE_PH) || defined(__TEST__)
    friend class RssiNode;
#endif
private:
#if defined(USE_UNIFIED_SENDBUFFER) || defined(USE_PH)
    SENDBUFFER defaultSendBuffer;
#endif
#if !defined(USE_UNIFIED_SENDBUFFER) || defined(__TEST__)
    PEAK_SENDBUFFER_IMPL defaultPeakSendBuffer;
    NADIR_SENDBUFFER_IMPL defaultNadirSendBuffer;
    DualSendBuffer dualSendBuffer;
#endif

    /** bit flags */
    uint8_t hasPending = 0;
#define PENDING_PEAK 2
#define PENDING_NADIR 1
#define PENDING_NONE 0

    void bufferPeak(bool force);
    void bufferNadir(bool force);

#ifdef __TEST__
public:
#endif
    SendBuffer<Extremum> *sendBuffer = nullptr;
    int8_t prevRssiChange = 0; // >0 for raising, <0 for falling
public:
    ExtremumType extremumType = NONE;
    Extremum peak = {0, 0, 0};
    Extremum nadir = {MAX_RSSI, 0, 0};

    History() {
#ifdef USE_UNIFIED_SENDBUFFER
        setSendBuffer(&defaultSendBuffer);
#else
        setSendBuffers(&defaultPeakSendBuffer, &defaultNadirSendBuffer);
#endif
    }
    inline void setSendBuffer(SendBuffer<Extremum> *buf) {
        sendBuffer = buf;
    }
#ifndef USE_UNIFIED_SENDBUFFER
    inline void setSendBuffers(ExtremumSendBuffer *peak, ExtremumSendBuffer *nadir) {
        dualSendBuffer.setSendBuffers(peak, nadir);
        setSendBuffer(&dualSendBuffer);
    }
#endif
    inline ExtremumType startNewPeak(rssi_t rssi, mtime_t ts);
    inline ExtremumType startNewNadir(rssi_t rssi, mtime_t ts);
    inline void bufferPeak() {bufferPeak(false);};
    inline void bufferNadir() {bufferNadir(false);};
    inline void recordRssiChange(int delta);
    ExtremumType nextToSendType();
    Extremum popNextToSend();
    inline bool checkForPeak(int rssiChange);
    inline bool checkForNadir(int rssiChange);
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
    LowPassFilter15Hz lpfFilter1;
    LowPassFilter50Hz lpfFilter2;

#if defined(USE_PH) || defined(__TEST__)
    ConnectedComponent ccs[(HISTORY_SIZE+1)/2];
#endif

    bool needsToSettle = true;
    mtime_t lastResetTimeMs;
    struct Settings settings;
    State state;
    History history;
    struct LastPass lastPass;

    Filter<rssi_t> *filter;

    ExtremumType updateHistory(int rssiChange);
    bool checkForCrossing(ExtremumType t, int rssiChange);
#if defined(USE_PH) || defined(__TEST__)
    bool checkForCrossing_ph(ExtremumType t, uint8_t threshold);
#endif
    bool checkForCrossing_old(rssi_t enterThreshold, rssi_t exitThreshold);
public:
    MedianFilter<rssi_t, 5, 0> medianFilter;
    Composite3Filter<rssi_t> defaultFilter;
    NoFilter<rssi_t> noFilter;

    bool volatile active = false; // Set true after initial WRITE_FREQUENCY command received

    RssiNode();
    void setFilter(Filter<rssi_t> *f);
    void start();
    bool isStateValid();
    /**
     * Restarts rssi peak tracking for node.
     */
    void resetState();
    bool process(rssi_t rssi, mtime_t ms);
    void endCrossing();

    struct Settings& getSettings() { return settings; }
    struct State& getState() { return state; }
    struct History& getHistory() { return history; }
    struct LastPass& getLastPass() { return lastPass; }
};
#endif
