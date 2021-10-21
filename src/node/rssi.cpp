#include "config.h"
#include "rssi.h"
#include "util/persistent-homology.h"
#ifdef USE_MQTT
#include "mqtt.h"
#include <stdio.h>
#endif

constexpr uint16_t MIN_TUNETIME = 35;  // after set freq need to wait this long before read RSSI

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

RssiResult RssiNode::process(rssi_t rssi, mtime_t ms)
{
    RssiResult result;

    filter->addRawValue(ms, rssi);
    if (filter->isFilled()) {
        const int rssiChange = state.readRssiFromFilter(filter);

        // wait until after-tune-delay time is fulfilled
        if (!needsToSettle)
        {  //don't start operations until after first WRITE_FREQUENCY command is received

            state.updateRssiStats();
            result.mode = settings.mode;
            switch (settings.mode) {
                case TIMER:
                    result = timerHandler(rssiChange);
                    break;
                case SCANNER:
                    result = scannerHandler(rssiChange);
                    break;
                case RAW:
                    result = rawHandler(rssiChange);
                    break;
            }
        }

        // check if RSSI is stable after tune
        if (needsToSettle && (ms - lastResetTimeMs) >= MIN_TUNETIME)
        {
            needsToSettle = false;  // don't need to check again until next freq change
        }
    }

    return result;
}

RssiResult RssiNode::timerHandler(const int rssiChange) {
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

    RssiResult result;
    result.crossing = crossing;
    return result;
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
    return checkForCrossing_ph(t, settings.enterAtLevel, settings.exitAtLevel);
#elif defined(__TEST__)
    if (settings.usePh) {
        return checkForCrossing_ph(t, settings.enterAtLevel, settings.exitAtLevel);
    } else {
        return checkForCrossing_old(settings.enterAtLevel, settings.exitAtLevel);
    }
#else
    return checkForCrossing_old(settings.enterAtLevel, settings.exitAtLevel);
#endif
}

#if defined(USE_PH) || defined(__TEST__)
bool RssiNode::checkForCrossing_ph(const ExtremumType currentType, const uint8_t enterThreshold, const uint8_t exitThreshold)
{
    const SENDBUFFER& sendBuffer = *((SENDBUFFER*)(history.sendBuffer));

    if (currentType == NONE || sendBuffer.size() == 0) {
        return state.crossing;
    }

#ifdef USE_MQTT
    int_fast16_t lifetimeSample = 0;
    bool triggered = false;
#endif
    const ExtremumType prevType = sendBuffer.typeAt(sendBuffer.size()-1);
    if (state.crossing && prevType == PEAK && currentType == NADIR) {
        int_fast8_t lastIdx = preparePhData(history.nadir.rssi);
        calculateNadirPersistentHomology<rssi_t,PH_HISTORY_SIZE>(phData, phSortedIdxs, lastIdx+1, ccs, &lastIdx);

        // find lifetime of last value when a nadir
        if (lastIdx < 0) {
            ConnectedComponent& cc = ccs[-lastIdx-1];
            const uint_fast8_t lastLifetime = phData[cc.death] - phData[cc.birth];
#ifdef USE_MQTT
            lifetimeSample = -lastLifetime;
#endif
            if (lastLifetime > exitThreshold) {
                endCrossing(lastLifetime);
#ifdef USE_MQTT
                triggered = true;
#endif
            }
        }
    } else if (!state.crossing && prevType == NADIR && currentType == PEAK) {
        int_fast8_t lastIdx = preparePhData(history.peak.rssi);
        calculatePeakPersistentHomology<rssi_t,PH_HISTORY_SIZE>(phData, phSortedIdxs, lastIdx+1, ccs, &lastIdx);

        // find lifetime of last value when a peak
        if (lastIdx < 0) {
            ConnectedComponent& cc = ccs[-lastIdx-1];
            const uint_fast8_t lastLifetime = phData[cc.birth] - phData[cc.death];
#ifdef USE_MQTT
            lifetimeSample = lastLifetime;
#endif
            if (lastLifetime > enterThreshold) {
                startCrossing(lastLifetime);
#ifdef USE_MQTT
                triggered = true;
#endif
            }
        }
    }

#ifdef USE_MQTT
    if (!triggered && lifetimeSample != 0 && state.rssiTimestamp % MQTT_SAMPLE_INTERVAL == 0)
    {
        char json[64] = "";
        int n = sprintf(json, "{\"rssi\": %u, \"timestamp\": \"%u\", \"lifetime\": %u}", state.rssi, state.rssiTimestamp, lifetimeSample);
        mqttPublish(*this, "sample", json, n);
    }
#endif

    return state.crossing;
}

int_fast8_t RssiNode::preparePhData(const rssi_t currentValue)
{
    const SENDBUFFER& sendBuffer = *((SENDBUFFER*)(history.sendBuffer));

    // copy history to fast array
    sendBuffer.copyRssi(phData);
    const int_fast8_t lastIdx = sendBuffer.size();
    // insert current value
    phData[lastIdx] = currentValue;

    // sort phData
    int_fast8_t j = lastIdx-1;
    for (; j>=0 && phData[sendBuffer.sortedIdxs[j]] > currentValue; j--) {
        phSortedIdxs[j+1] = sendBuffer.sortedIdxs[j];
    }
    phSortedIdxs[j+1] = lastIdx;
    for (; j>=0; j--) {
        phSortedIdxs[j] = sendBuffer.sortedIdxs[j];
    }

    return lastIdx;
}
#endif

bool RssiNode::checkForCrossing_old(const rssi_t enterThreshold, const rssi_t exitThreshold)
{
    /*** crossing transition ***/

    if ((!state.crossing) && state.rssi >= enterThreshold)
    {
        // quad is going through the gate (lap pass starting)
        startCrossing(state.rssi);
    }
    else if (state.crossing && state.rssi < exitThreshold)
    {
        // quad has left the gate
        endCrossing(state.rssi);
    }
#ifdef USE_MQTT
    else if (state.rssiTimestamp % MQTT_SAMPLE_INTERVAL == 0)
    {
        char json[64] = "";
        int n = sprintf(json, "{\"rssi\": %u, \"timestamp\": \"%u\"}", state.rssi, state.rssiTimestamp);
        mqttPublish(*this, "sample", json, n);
    }
#endif

    return state.crossing;
}

bool RssiNode::isCrossing()
{
    return state.crossing;
}

void RssiNode::startCrossing(uint8_t trigger)
{
    state.crossing = true;
#ifdef USE_MQTT
    char json[64] = "";
#if defined(USE_PH)
    int n = sprintf(json, "{\"lap\": %u, \"rssi\": %u, \"timestamp\": \"%u\", \"lifetime\": %u}", lastPass.lap+1, state.rssi, state.rssiTimestamp, trigger);
#else
    int n = sprintf(json, "{\"lap\": %u, \"rssi\": %u, \"timestamp\": \"%u\"}", lastPass.lap+1, state.rssi, state.rssiTimestamp);
#endif
    mqttPublish(*this, "enter", json, n);
#endif
}

/*** Function called when crossing ends (by RSSI or I2C command). */
void RssiNode::endCrossing(uint8_t trigger)
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

#ifdef USE_MQTT
    char json[64] = "";
#if defined(USE_PH)
    int n = sprintf(json, "{\"lap\": %u, \"rssi\": %u, \"timestamp\": \"%u\", \"lifetime\": -%u}", lastPass.lap, state.rssi, state.rssiTimestamp, trigger);
#else
    int n = sprintf(json, "{\"lap\": %u, \"rssi\": %u, \"timestamp\": \"%u\"}", lastPass.lap, state.rssi, state.rssiTimestamp);
#endif
    mqttPublish(*this, "exit", json, n);

    n = sprintf(json, "{\"rssi\": %u, \"lap\": %u, \"timestamp\": \"%u\"}", lastPass.rssiPeak, lastPass.lap, lastPass.timestamp);
    mqttPublish(*this, "pass", json, n);
#endif
}

RssiResult RssiNode::scannerHandler(const int rssiChange) {
    freq_t nextFreq = updateScanHistory(settings.vtxFreq);
    settings.vtxFreq = nextFreq;
    RssiResult result;
    result.nextFreq = nextFreq;
    return result;
}

freq_t RssiNode::updateScanHistory(const freq_t freq)
{
#ifdef SCAN_HISTORY
    if (!scanHistory.isFull())
    {
        FreqRssi f_r = {freq, state.rssi};
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            scanHistory.push(f_r);
        }

        freq_t nextFreq = freq + SCAN_FREQ_INCR;
        if (nextFreq > MAX_SCAN_FREQ) {
            nextFreq = MIN_SCAN_FREQ;
        }
        return nextFreq;
    } else {
        return 0;
    }
#endif
}

RssiResult RssiNode::rawHandler(const int rssiChange) {
    updateRssiHistory();
    RssiResult result;
    result.none = 0;
    return result;
}

void RssiNode::updateRssiHistory()
{
#ifdef RSSI_HISTORY
    if (!rssiHistoryComplete) {
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            if (!rssiHistory.isFull()) {
                rssiHistory.push(state.rssi);
            } else {
                rssiHistoryComplete = true;
            }
        }
    }
#endif
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
