#include "config.h"
#include "rssi.h"
#include "util/persistent-homology.h"

#define MIN_TUNETIME 35  // after set freq need to wait this long before read RSSI

inline void initExtremum(Extremum& e, rssi_t rssi, mtime_t ts)
{
    e.rssi = rssi;
    e.firstTime = ts;
    e.duration = 0;
}

RssiNode::RssiNode() : defaultFilter(lpfFilter1, lpfFilter2, medianFilter)
{
    setFilter(&defaultFilter);
}

void RssiNode::setFilter(Filter<rssi_t> *f)
{
    filter = f;
}

void RssiNode::start(const mtime_t ms, const utime_t us)
{
    lastResetTimeMs = ms;
    state.lastloopMicros = us;
}

bool RssiNode::isStateValid()
{
    return state.nodeRssiNadir <= state.rssi && state.rssi <= state.nodeRssiPeak;
}

void RssiNode::resetState(const mtime_t ms)
{
    filter->reset();
    state.reset();
    history.reset();
    needsToSettle = true;
    lastResetTimeMs = ms;
}

bool RssiNode::process(rssi_t rssi, mtime_t ms)
{
    filter->addRawValue(ms, rssi);
    if (filter->isFilled()) {
        const int rssiChange = state.readRssiFromFilter(filter);

        // wait until after-tune-delay time is fulfilled
        if (!needsToSettle)
        {  //don't start operations until after first WRITE_FREQUENCY command is received

            state.updateRssiStats();
            const ExtremumType currentType = updateHistory(rssiChange);
            const bool crossing = checkForCrossing(currentType, rssiChange);

            /*** pass processing **/

            if (crossing)
            {  //lap pass is in progress
                // Find the peak rssi and the time it occured during a crossing event
                if (state.rssi > state.passPeak.rssi)
                {
                    // this is first time this peak RSSI value was seen, so save value and timestamp
                    initExtremum(state.passPeak, state.rssi, state.rssiTimestamp);
                }
                else if (state.rssi == state.passPeak.rssi)
                {
                    // if at max peak for more than one iteration then track duration
                    // so middle-timestamp value can be returned
                    state.passPeak.duration = toDuration(state.rssiTimestamp - state.passPeak.firstTime);
                }
            }
            else
            {
                // track lowest rssi seen since end of last pass
                state.passRssiNadir = min((rssi_t)state.rssi, (rssi_t)state.passRssiNadir);
            }
        }

        // check if RSSI is stable after tune
        if (needsToSettle && (ms - lastResetTimeMs) >= MIN_TUNETIME)
        {
            needsToSettle = false;  // don't need to check again until next freq change
        }
    }

    return state.crossing;
}

ExtremumType RssiNode::updateHistory(const int rssiChange)
{
    ExtremumType etype;
    if (rssiChange > 0)
    {  // RSSI is rising
        // whenever history is rising, record the time and value as a peak
        etype = history.startNewPeak(state.rssi, state.rssiTimestamp);

        // if RSSI was falling or unchanged, but it's rising now, we found a nadir
        // copy the values to be sent in the next loop
        history.checkForNadir(rssiChange);
    }
    else if (rssiChange < 0)
    {  // RSSI is falling
        // whenever history is falling, record the time and value as a nadir
        etype = history.startNewNadir(state.rssi, state.rssiTimestamp);

        // if RSSI was rising or unchanged, but it's falling now, we found a peak
        // copy the values to be sent in the next loop
        history.checkForPeak(rssiChange);
    }
    else
    {  // RSSI is equal
        switch (history.extremumType) {
            case PEAK:
                history.peak.duration = toDuration(state.rssiTimestamp - history.peak.firstTime);
                if (history.peak.duration == MAX_DURATION)
                {
                    history.startNewPeak(state.rssi, state.rssiTimestamp);
                }
                break;
            case NADIR:
                history.nadir.duration = toDuration(state.rssiTimestamp - history.nadir.firstTime);
                if (history.nadir.duration == MAX_DURATION)
                {
                    history.startNewNadir(state.rssi, state.rssiTimestamp);
                }
                break;
            default:
                initExtremum(history.peak, state.rssi, state.rssiTimestamp);
                initExtremum(history.nadir, state.rssi, state.rssiTimestamp);
                break;
        }
        etype = history.extremumType;
    }

    history.recordRssiChange(rssiChange);

    // try to buffer latest peak/nadir (don't overwrite any unsent peak/nadir)
    history.bufferPeak();
    history.bufferNadir();

    return etype;
}

bool RssiNode::checkForCrossing(const ExtremumType t, const int rssiChange)
{
#if defined(USE_PH)
    uint8_t level = (settings.enterAtLevel == settings.exitAtLevel) ? settings.enterAtLevel : 20;
    return checkForCrossing_ph(t, level);
#elif defined(__TEST__)
    if (settings.enterAtLevel == settings.exitAtLevel) {
        return checkForCrossing_ph(t, settings.enterAtLevel);
    } else {
        return checkForCrossing_old(settings.enterAtLevel, settings.exitAtLevel);
    }
#else
    return checkForCrossing_old(settings.enterAtLevel, settings.exitAtLevel);
#endif
}

#if defined(USE_PH) || defined(__TEST__)
bool RssiNode::checkForCrossing_ph(const ExtremumType currentType, const uint8_t threshold)
{
    const SENDBUFFER& sendBuffer = *((SENDBUFFER*)(history.sendBuffer));

    if (currentType == NONE || sendBuffer.size() == 0) {
        return state.crossing;
    }

    const ExtremumType prevType = sendBuffer.typeAt(sendBuffer.size()-1);
    if (state.crossing && prevType == PEAK && currentType == NADIR) {
        int_fast8_t lastIdx = sendBuffer.size();
        phData[lastIdx] = history.nadir.rssi;
        for (int_fast8_t i=lastIdx-1; i>=0; i--) {
            phData[i] = sendBuffer[i].rssi;
        }
        calculateNadirPersistentHomology<rssi_t,PH_HISTORY_SIZE>(phData, lastIdx+1, ccs, &lastIdx);

        // find lifetime of last value when a nadir
        if (lastIdx < 0) {
            ConnectedComponent& cc = ccs[-lastIdx-1];
            const uint_fast8_t lastLife = phData[cc.death] - phData[cc.birth];
            if (lastLife > threshold) {
                endCrossing();
            }
        }
    } else if (!state.crossing && prevType == NADIR && currentType == PEAK) {
        int_fast8_t lastIdx = sendBuffer.size();
        phData[lastIdx] = history.peak.rssi;
        for (int_fast8_t i=lastIdx-1; i>=0; i--) {
            phData[i] = sendBuffer[i].rssi;
        }
        calculatePeakPersistentHomology<rssi_t,PH_HISTORY_SIZE>(phData, lastIdx+1, ccs, &lastIdx);

        // find lifetime of last value when a peak
        if (lastIdx < 0) {
            ConnectedComponent& cc = ccs[-lastIdx-1];
            const uint_fast8_t lastLife = phData[cc.birth] - phData[cc.death];
            if (lastLife > threshold) {
                state.crossing = true;
            }
        }
    }

    return state.crossing;
}
#endif

bool RssiNode::checkForCrossing_old(const rssi_t enterThreshold, const rssi_t exitThreshold)
{
    /*** crossing transition ***/

    if ((!state.crossing) && state.rssi >= enterThreshold)
    {
        state.crossing = true;  // quad is going through the gate (lap pass starting)
    }
    else if (state.crossing && state.rssi < exitThreshold)
    {
        // quad has left the gate
        endCrossing();
    }

    return state.crossing;
}

/*** Function called when crossing ends (by RSSI or I2C command). */
void RssiNode::endCrossing()
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
    state.resetPass();
}


int State::readRssiFromFilter(Filter<rssi_t>* filter)
{
    lastRssi = rssi;
    rssi = filter->getFilteredValue();
    rssiTimestamp = filter->getFilterTimestamp();

    // ensure signed arithmetic
    return (int)rssi - (int)lastRssi;
}

/*** node lifetime RSSI max/min ***/
void State::updateRssiStats() {
    if (rssi > nodeRssiPeak)
    {
        nodeRssiPeak = rssi;
    }

    if (rssi < nodeRssiNadir)
    {
        nodeRssiNadir = rssi;
    }

#ifdef RSSI_HISTORY
    if (!rssiHistoryComplete) {
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            if (!rssiHistory.isFull()) {
                rssiHistory.push(rssi);
            } else {
                rssiHistoryComplete = true;
            }
        }
    }
#endif
}

/*** Calculate the time it takes to run the main loop. */
void State::updateLoopTime(utime_t loopMicros)
{
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        loopTimeMicros = loopMicros - lastloopMicros;
    }
    lastloopMicros = loopMicros;
}

void State::resetPass()
{
    crossing = false;
    invalidatePeak(passPeak);
    passRssiNadir = MAX_RSSI;
}

void State::reset()
{
    resetPass();
    nodeRssiPeak = 0;
    nodeRssiNadir = MAX_RSSI;
}

ExtremumType History::startNewPeak(rssi_t rssi, mtime_t ts) {
  // must buffer latest peak to prevent losing it
  bufferPeak(true);
  // reset peak
  initExtremum(peak, rssi, ts);
  extremumType = PEAK;
  return extremumType;
}

ExtremumType History::startNewNadir(rssi_t rssi, mtime_t ts) {
  // must buffer latest nadir to prevent losing it
  bufferNadir(true);
  // reset nadir
  initExtremum(nadir, rssi, ts);
  extremumType = NADIR;
  return extremumType;
}

void History::bufferPeak(bool force)
{
    if (hasPending & PENDING_PEAK)
    {
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            bool buffered = sendBuffer->addPeak(peak, force);
            if (buffered || force)
            {
                hasPending &= ~PENDING_PEAK;
            }
        }
    }
}

void History::bufferNadir(bool force)
{
    if (hasPending & PENDING_NADIR)
    {
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            bool buffered = sendBuffer->addNadir(nadir, force);
            if (buffered || force)
            {
                hasPending &= ~PENDING_NADIR;
            }
        }
    }
}

void History::recordRssiChange(int delta)
{
  // clamp to prevent overflow
  prevRssiChange = constrain(delta, -127, 127);
}

ExtremumType History::nextToSendType()
{
    ExtremumType t;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        t = sendBuffer->nextType();
    }
    return t;
}

Extremum History::popNextToSend()
{
    Extremum e;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        e = sendBuffer->popNext();
    }
    return e;
}

bool History::checkForPeak(const int rssiChange)
{
  if (prevRssiChange >= 0 && rssiChange < 0 && isPeakValid(peak))
  {  // was rising or unchanged
      // declare a new peak
      hasPending |= PENDING_PEAK;
      return true;
  }
  else
  {
      return false;
  }
}

bool History::checkForNadir(const int rssiChange)
{
  if (prevRssiChange <= 0 && rssiChange > 0 && isNadirValid(nadir))
  {  // was falling or unchanged
      // declare a new nadir
      hasPending |= PENDING_NADIR;
      return true;
  }
  else
  {
      return false;
  }
}

void History::reset()
{
    extremumType = NONE;
    invalidatePeak(peak);
    invalidateNadir(nadir);
    hasPending = PENDING_NONE;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        sendBuffer->clear();
    }
    prevRssiChange = 0;
}
