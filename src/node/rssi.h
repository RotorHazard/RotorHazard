#ifndef rssi_h
#define rssi_h

#include "config.h"
#include "util/persistent-homology.h"
#include "util/filter.h"
#include "util/median-filter.h"
#include "util/lowpass10hz-filter.h"
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

constexpr uint16_t MAX_DURATION = 0xFFFF;
inline uint16_t toDuration(uint32_t ms) { return uint16_t(min(ms, uint32_t(MAX_DURATION))); }

#if TARGET == AVR_TARGET
constexpr uint8_t HISTORY_SIZE = 12;
#else
constexpr uint8_t HISTORY_SIZE = 6;
#endif
constexpr uint8_t PH_HISTORY_SIZE = (HISTORY_SIZE+1); // should be odd, +1 to allow for current value
constexpr uint16_t RSSI_HISTORY_SIZE = 800; // NB: need to leave about a 100 bytes free RAM
constexpr uint8_t SCAN_HISTORY_SIZE = 4;

#define USE_UNIFIED_SENDBUFFER
#ifdef __TEST__
#undef USE_UNIFIED_SENDBUFFER
#endif

#if defined(USE_PH) || defined(__TEST__)
#define SENDBUFFER SortedUnifiedSendBuffer<HISTORY_SIZE>
#else
#define SENDBUFFER UnifiedSendBuffer<Extremum,HISTORY_SIZE>
#endif

#define PEAK_SENDBUFFER_SINGLE SinglePeakSendBuffer
#define PEAK_SENDBUFFER_MULTI MultiPeakSendBuffer<HISTORY_SIZE/2>
#define NADIR_SENDBUFFER_SINGLE SingleNadirSendBuffer
#define NADIR_SENDBUFFER_MULTI MultiNadirSendBuffer<HISTORY_SIZE/2>

//select the send buffer to use here
#define PEAK_SENDBUFFER_IMPL PEAK_SENDBUFFER_MULTI
#define NADIR_SENDBUFFER_IMPL NADIR_SENDBUFFER_MULTI

constexpr freq_t MIN_SCAN_FREQ = 5645;
constexpr freq_t MAX_SCAN_FREQ = 5945;
constexpr uint16_t SCAN_FREQ_INCR = 5;

enum Mode
{
    TIMER = 0,
    SCANNER = 1,
    RAW = 2
};

#ifdef USE_PH
#define DEFAULT_ENTER_AT_LEVEL 40
#define DEFAULT_EXIT_AT_LEVEL 40
#else
#define DEFAULT_ENTER_AT_LEVEL 96
#define DEFAULT_EXIT_AT_LEVEL 80
#endif

struct Settings
{
    freq_t volatile vtxFreq = 5800;
    // lap pass begins when RSSI is at or above this level
    rssi_t volatile enterAtLevel = DEFAULT_ENTER_AT_LEVEL;
    // lap pass ends when RSSI goes below this level
    rssi_t volatile exitAtLevel = DEFAULT_EXIT_AT_LEVEL;
    Mode volatile mode = TIMER;
#ifdef __TEST__
    bool volatile usePh = false;
#endif
};

class State
{
    friend class RssiNode;
#ifdef __TEST__
public:
#else
private:
#endif
    bool volatile crossing = false; // True when the quad is going through the gate
public:
    // variables to track the loop time
    utime_t volatile loopTimeMicros = 0;
    utime_t lastloopMicros = 0;

    rssi_t volatile rssi = 0; // Smoothed rssi value
    mtime_t rssiTimestamp = 0; // timestamp of the smoothed value
    rssi_t lastRssi = 0;

    Extremum passPeak = {0, 0, 0}; // peak seen during current pass - only valid if pass.rssi != 0
    rssi_t passRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since end of last pass

    rssi_t volatile nodeRssiPeak = 0; // peak smoothed rssi seen since the node frequency was set
    rssi_t volatile nodeRssiNadir = MAX_RSSI; // lowest smoothed rssi seen since the node frequency was set

    /**
     * Returns the RSSI change since the last reading.
     */
    inline int readRssiFromFilter(Filter<rssi_t>* f);
    inline void updateRssiStats();
    void updateLoopTime(utime_t loopMicros);
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
    void setSendBuffer(SendBuffer<Extremum> *buf) {
        sendBuffer = buf;
    }
#ifndef USE_UNIFIED_SENDBUFFER
    void setSendBuffers(ExtremumSendBuffer *peak, ExtremumSendBuffer *nadir) {
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

enum PendingOperations: uint8_t
{
    NO_OPS          = 0x00,
    FREQ_SET        = 0x01,
    FREQ_CHANGED    = 0x02
};

class RssiNode
{
private:
    LowPassFilter15Hz lpfFilter1;
    LowPassFilter50Hz lpfFilter2;

#if defined(USE_PH) || defined(__TEST__)
    ConnectedComponent ccs[(PH_HISTORY_SIZE+1)/2];
#ifdef __TEST__
public:
#endif
    rssi_t phData[PH_HISTORY_SIZE];
    uint_fast8_t phSortedIdxs[PH_HISTORY_SIZE];
#ifdef __TEST__
private:
#endif
#endif

    bool needsToSettle = true;
    mtime_t lastResetTimeMs;
    Settings settings;
    State state;
    History history;
    LastPass lastPass;

    Filter<rssi_t> *filter;

    inline bool timerHandler(const int rssiChange);
    inline bool scannerHandler(const int rssiChange);
    inline bool rawHandler(const int rssiChange);
    inline ExtremumType updateHistory(int rssiChange);
    inline void updateScanHistory(freq_t f);
    inline void updateRssiHistory();
    bool checkForCrossing(ExtremumType t, int rssiChange);
#if defined(USE_PH) || defined(__TEST__)
#ifdef __TEST__
public:
#endif
    bool checkForCrossing_ph(ExtremumType t, uint8_t enterThreshold, uint8_t exitThreshold);
    int_fast8_t preparePhData(rssi_t currentValue);
#ifdef __TEST__
private:
#endif
#endif
    bool checkForCrossing_old(rssi_t enterThreshold, rssi_t exitThreshold);
public:
    MedianFilter<rssi_t, 5, 0> medianFilter;
    Composite3Filter<rssi_t> defaultFilter;
    NoFilter<rssi_t> noFilter;

#ifdef SCAN_HISTORY
    CircularBuffer<FreqRssi,SCAN_HISTORY_SIZE> scanHistory;
#endif
#ifdef RSSI_HISTORY
    CircularBuffer<rssi_t,RSSI_HISTORY_SIZE> rssiHistory;
    bool volatile rssiHistoryComplete = false;
#endif

    bool active = false; // Set true after initial frequency is set
    uint8_t pendingOps = NO_OPS;

    RssiNode();
    RssiNode(const RssiNode&) = delete;
    RssiNode(RssiNode&&) = delete;
    RssiNode& operator=(const RssiNode&) = delete;
    RssiNode& operator=(RssiNode&&) = delete;

    void setFilter(Filter<rssi_t> *f);
    void start(mtime_t ms, utime_t us);
    bool isStateValid();
    /**
     * Restarts rssi peak tracking for node.
     */
    void resetState(mtime_t ms);
    bool process(rssi_t rssi, mtime_t ms);
    bool isCrossing();
    void startCrossing();
    void endCrossing();

    Settings& getSettings() { return settings; }
    State& getState() { return state; }
    History& getHistory() { return history; }
    LastPass& getLastPass() { return lastPass; }
};
#endif
