#include "config.h"
#include "rssi.h"

//select the filter to use here
//#include "median-filter.h"
//#include "lowpass20hz-filter.h"
//#include "lowpass50hz-filter.h"
#include "lowpass100hz-filter.h"
//#include "no-filter.h"

struct Settings settings;
struct State state;
struct History history;
struct LastPass lastPass;

Filter<rssi_t> *filter = &_filter;

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
    state.passPeak.rssi = 0;
    state.passRssiNadir = MAX_RSSI;
    state.nodeRssiPeak = 0;
    state.nodeRssiNadir = MAX_RSSI;
    history.hasPendingPeak = false;
    history.peakSend.rssi = 0;
    history.hasPendingNadir = false;
    history.nadirSend.rssi = MAX_RSSI;
}

static void bufferHistoricPeak(bool force)
{
    if (history.hasPendingPeak)
    {
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            if (!isPeakValid(history.peakSend))
            {
                // no current peak to send so just overwrite
                history.peakSend = history.peak;
                history.hasPendingPeak = false;
            }
            else if (force)
            {
                // must do something
                if (history.peak.rssi > history.peakSend.rssi)
                {
                    // prefer higher peak
                    history.peakSend = history.peak;
                }
                else if (history.peak.rssi == history.peakSend.rssi)
                {
                    // merge
                    history.peakSend.duration = endTime(history.peak) - history.peakSend.firstTime;
                }
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
            if (!isNadirValid(history.nadirSend))
            {
                // no current nadir to send so just overwrite
                history.nadirSend = history.nadir;
                history.hasPendingNadir = false;
            }
            else if (force)
            {
                // must do something
                if (history.nadir.rssi < history.nadirSend.rssi)
                {
                    // prefer lower nadir
                    history.nadirSend = history.nadir;
                }
                else if (history.nadir.rssi == history.nadirSend.rssi)
                {
                    // merge
                    history.nadirSend.duration = endTime(history.nadir) - history.nadirSend.firstTime;
                }
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
