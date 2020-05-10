#include "config.h"
#include "rssi.h"
#include "util/median-filter.h"
#include "util/lowpass20hz-filter.h"
#include "util/lowpass50hz-filter.h"
#include "util/lowpass100hz-filter.h"
#include "util/no-filter.h"
#include "util/single-sendbuffer.h"
#include "util/multi-sendbuffer.h"

#define FILTER_NONE NoFilter<rssi_t>
#define FILTER_MEDIAN MedianFilter<rssi_t, SmoothingSamples, 0>
#define FILTER_100 LowPassFilter100Hz
#define FILTER_50 LowPassFilter50Hz
#define FILTER_20 LowPassFilter20Hz

//select the filter to use here
#define FILTER_IMPL FILTER_MEDIAN

#define PEAK_SENDBUFFER_SINGLE SinglePeakSendBuffer
#define PEAK_SENDBUFFFER_MULTI MultiSendBuffer<Extremum,10>
#define NADIR_SENDBUFFER_SINGLE SingleNadirSendBuffer
#define NADIR_SENDBUFFFER_MULTI MultiSendBuffer<Extremum,10>

//select the send buffer to use here
#define PEAK_SENDBUFFER_IMPL PEAK_SENDBUFFER_SINGLE
#define NADIR_SENDBUFFER_IMPL NADIR_SENDBUFFER_SINGLE


FILTER_IMPL defaultFilter;
PEAK_SENDBUFFER_IMPL defaultPeakSendBuffer;
NADIR_SENDBUFFER_IMPL defaultNadirSendBuffer;

struct Settings settings;
struct State state;
struct History history = {
    {0, 0, 0}, false, &defaultPeakSendBuffer,
    {MAX_RSSI, 0, 0}, false, &defaultNadirSendBuffer,
    0
};
struct LastPass lastPass;

static Filter<rssi_t> *filter = &defaultFilter;

void rssiSetFilter(Filter<rssi_t> *f)
{
    filter = f;
}

void rssiSetSendBuffers(SendBuffer<Extremum> *peak, SendBuffer<Extremum> *nadir)
{
    history.peakSend = peak;
    history.nadirSend = nadir;
}

void rssiInit()
{
    state.lastloopMicros = micros();
}

bool rssiStateValid()
{
    return state.nodeRssiNadir <= state.rssi && state.rssi <= state.nodeRssiPeak;
}

void rssiStateReset()
{
    state.crossing = false;
    invalidatePeak(state.passPeak);
    state.passRssiNadir = MAX_RSSI;
    state.nodeRssiPeak = 0;
    state.nodeRssiNadir = MAX_RSSI;
    invalidatePeak(history.peak);
    history.hasPendingPeak = false;
    history.peakSend->clear();
    invalidateNadir(history.nadir);
    history.hasPendingNadir = false;
    history.nadirSend->clear();
}

static void bufferHistoricPeak(bool force)
{
    if (history.hasPendingPeak)
    {
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            bool buffered = history.peakSend->addIfAvailable(history.peak);
            if (buffered)
            {
                history.hasPendingPeak = false;
            }
            else if (force)
            {
                history.peakSend->addOrDiscard(history.peak);
                history.hasPendingPeak = false;
            }
        }
    }
}

static void bufferHistoricNadir(bool force)
{
    if (history.hasPendingNadir)
    {
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            bool buffered = history.nadirSend->addIfAvailable(history.nadir);
            if (buffered)
            {
                history.hasPendingNadir = false;
            }
            else if (force)
            {
                history.nadirSend->addOrDiscard(history.nadir);
                history.hasPendingNadir = false;
            }
        }
    }
}

static void initExtremum(Extremum *e)
{
    e->rssi = state.rssi;
    e->firstTime = state.rssiTimestamp;
    e->duration = 0;
}

bool rssiProcess(rssi_t rssi, mtime_t millis)
{
    filter->addRawValue(millis, rssi);

    if (filter->isFilled() && state.activatedFlag)
    {  //don't start operations until after first WRITE_FREQUENCY command is received

        state.lastRssi = state.rssi;
        state.rssi = filter->getFilteredValue();
        state.rssiTimestamp = filter->getFilterTimestamp();

        /*** update history ***/

        const int rssiChange = state.rssi - state.lastRssi;
        if (rssiChange > 0)
        {  // RSSI is rising
            // must buffer latest peak to prevent losing it (overwriting any unsent peak)
            bufferHistoricPeak(true);

            initExtremum(&(history.peak));

            // if RSSI was falling or unchanged, but it's rising now, we found a nadir
            // copy the values to be sent in the next loop
            if (history.rssiChange <= 0)
            {  // was falling or unchanged
                // declare a new nadir
                history.hasPendingNadir = true;
            }

        }
        else if (rssiChange < 0)
        {  // RSSI is falling
            // must buffer latest nadir to prevent losing it (overwriting any unsent nadir)
            bufferHistoricNadir(true);

            // whenever history is falling, record the time and value as a nadir
            initExtremum(&(history.nadir));

            // if RSSI was rising or unchanged, but it's falling now, we found a peak
            // copy the values to be sent in the next loop
            if (history.rssiChange >= 0)
            {  // was rising or unchanged
                // declare a new peak
                history.hasPendingPeak = true;
            }

        }
        else
        {  // RSSI is equal
            if (state.rssi == history.peak.rssi)
            {  // is peak
                history.peak.duration = constrain(state.rssiTimestamp - history.peak.firstTime, 0,
                        MAX_DURATION);
                if (history.peak.duration == MAX_DURATION)
                {
                    bufferHistoricPeak(true);
                    initExtremum(&(history.peak));
                }
            }
            else if (state.rssi == history.nadir.rssi)
            {  // is nadir
                history.nadir.duration = constrain(state.rssiTimestamp - history.nadir.firstTime, 0,
                        MAX_DURATION);
                if (history.nadir.duration == MAX_DURATION)
                {
                    bufferHistoricNadir(true);
                    initExtremum(&(history.nadir));
                }
            }
        }

        // clamp to prevent overflow
        history.rssiChange = constrain(rssiChange, -127, 127);

        // try to buffer latest peak/nadir (don't overwrite any unsent peak/nadir)
        bufferHistoricPeak(false);
        bufferHistoricNadir(false);

        /*** node lifetime RSSI max/min ***/

        if (state.rssi > state.nodeRssiPeak)
        {
            state.nodeRssiPeak = state.rssi;
        }

        if (state.rssi < state.nodeRssiNadir)
        {
            state.nodeRssiNadir = state.rssi;
        }

        /*** crossing transition ***/

        if ((!state.crossing) && state.rssi >= settings.enterAtLevel)
        {
            state.crossing = true;  // quad is going through the gate (lap pass starting)
        }
        else if (state.crossing && state.rssi < settings.exitAtLevel)
        {
            // quad has left the gate
            rssiEndCrossing();
        }

        /*** pass processing **/

        if (state.crossing)
        {  //lap pass is in progress
            // Find the peak rssi and the time it occured during a crossing event
            if (state.rssi > state.passPeak.rssi)
            {
                // this is first time this peak RSSI value was seen, so save value and timestamp
                initExtremum(&(state.passPeak));
            }
            else if (state.rssi == state.passPeak.rssi)
            {
                // if at max peak for more than one iteration then track duration
                // so middle-timestamp value can be returned
                state.passPeak.duration = constrain(state.rssiTimestamp - state.passPeak.firstTime,
                        0, MAX_DURATION);
            }
        }
        else
        {
            // track lowest rssi seen since end of last pass
            state.passRssiNadir = min(state.rssi, state.passRssiNadir);
        }
    }

    // Calculate the time it takes to run the main loop
    utime_t loopMicros = micros();
    state.loopTimeMicros = loopMicros - state.lastloopMicros;
    state.lastloopMicros = loopMicros;

    return state.crossing;
}

// Function called when crossing ends (by RSSI or I2C command)
void rssiEndCrossing()
{
    // save values for lap pass
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        lastPass.rssiPeak = state.passPeak.rssi;
        // lap timestamp is between first and last peak RSSI
        lastPass.timestamp = state.passPeak.firstTime + state.passPeak.duration / 2;
        lastPass.rssiNadir = state.passRssiNadir;
        lastPass.lap = lastPass.lap + 1;
    }

    // reset lap-pass variables
    state.crossing = false;
    state.passPeak.rssi = 0;
    state.passRssiNadir = MAX_RSSI;
}
