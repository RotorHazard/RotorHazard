#include "config.h"
#include "rssi.h"

inline void initExtremum(Extremum& e, rssi_t rssi, mtime_t ts)
{
    e.rssi = rssi;
    e.firstTime = ts;
    e.duration = 0;
}

RssiNode::RssiNode()
{
    setFilter(&defaultFilter);
}

void RssiNode::setFilter(Filter<rssi_t> *f)
{
    filter = f;
}

void RssiNode::start()
{
    state.lastloopMicros = micros();
}

bool RssiNode::isStateValid()
{
    return state.nodeRssiNadir <= state.rssi && state.rssi <= state.nodeRssiPeak;
}

void RssiNode::resetState()
{
    state.reset();
    history.reset();
}

bool RssiNode::process(rssi_t rssi, mtime_t millis)
{
    filter->addRawValue(millis, rssi);

    if (filter->isFilled() && state.activatedFlag)
    {  //don't start operations until after first WRITE_FREQUENCY command is received

        const int rssiChange = state.readRssiFromFilter(filter);

        /*** update history ***/

        if (rssiChange > 0)
        {  // RSSI is rising

            // whenever history is rising, record the time and value as a peak
            history.startNewPeak(state.rssi, state.rssiTimestamp);

            // if RSSI was falling or unchanged, but it's rising now, we found a nadir
            // copy the values to be sent in the next loop
            history.checkForNadir();
        }
        else if (rssiChange < 0)
        {  // RSSI is falling

            // whenever history is falling, record the time and value as a nadir
            history.startNewNadir(state.rssi, state.rssiTimestamp);

            // if RSSI was rising or unchanged, but it's falling now, we found a peak
            // copy the values to be sent in the next loop
            history.checkForPeak();
        }
        else
        {  // RSSI is equal
            if (state.rssi == history.peak.rssi)
            {  // is peak
                history.peak.duration = constrain(state.rssiTimestamp - history.peak.firstTime, 0,
                        MAX_DURATION);
                if (history.peak.duration == MAX_DURATION)
                {
                    history.startNewPeak(state.rssi, state.rssiTimestamp);
                }
            }
            else if (state.rssi == history.nadir.rssi)
            {  // is nadir
                history.nadir.duration = constrain(state.rssiTimestamp - history.nadir.firstTime, 0,
                        MAX_DURATION);
                if (history.nadir.duration == MAX_DURATION)
                {
                    history.startNewNadir(state.rssi, state.rssiTimestamp);
                }
            }
        }

        history.recordRssiChange(rssiChange);

        // try to buffer latest peak/nadir (don't overwrite any unsent peak/nadir)
        history.bufferPeak();
        history.bufferNadir();

        /*** crossing transition ***/

        if ((!state.crossing) && state.rssi >= settings.enterAtLevel)
        {
            state.crossing = true;  // quad is going through the gate (lap pass starting)
        }
        else if (state.crossing && state.rssi < settings.exitAtLevel)
        {
            // quad has left the gate
            endCrossing();
        }

        /*** pass processing **/

        if (state.crossing)
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
    state.updateLoopTime(loopMicros);

    return state.crossing;
}

// Function called when crossing ends (by RSSI or I2C command)
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

    /*** node lifetime RSSI max/min ***/

    if (rssi > nodeRssiPeak)
    {
        nodeRssiPeak = rssi;
    }

    if (rssi < nodeRssiNadir)
    {
        nodeRssiNadir = rssi;
    }

    // ensure signed arithmetic
    return (int)rssi - (int)lastRssi;  
}

void State::updateLoopTime(utime_t loopMicros)
{
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        loopTimeMicros = loopMicros - lastloopMicros;
        minLoopTimeMicros = min(loopTimeMicros, minLoopTimeMicros);
        maxLoopTimeMicros = max(loopTimeMicros, maxLoopTimeMicros);
    }
    lastloopMicros = loopMicros;
}

void State::resetPass()
{
    crossing = false;
    passPeak.rssi = 0;
    passRssiNadir = MAX_RSSI;
}

void State::reset()
{
    crossing = false;
    invalidatePeak(passPeak);
    passRssiNadir = MAX_RSSI;
    nodeRssiPeak = 0;
    nodeRssiNadir = MAX_RSSI;
}


History::History()
{
    setSendBuffers(&defaultPeakSendBuffer, &defaultNadirSendBuffer);
}

void History::setSendBuffers(SendBuffer<Extremum> *peak, SendBuffer<Extremum> *nadir)
{
    peakSend = peak;
    nadirSend = nadir;
}

void History::startNewPeak(rssi_t rssi, mtime_t ts) {
  // must buffer latest peak to prevent losing it
  bufferPeak(true);
  // reset peak
  initExtremum(peak, rssi, ts);
}

void History::startNewNadir(rssi_t rssi, mtime_t ts) {
  // must buffer latest nadir to prevent losing it
  bufferNadir(true);
  // reset nadir
  initExtremum(nadir, rssi, ts);
}

void History::bufferPeak(bool force)
{
    if (hasPendingPeak)
    {
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            bool buffered = peakSend->addIfAvailable(peak);
            if (buffered)
            {
                hasPendingPeak = false;
            }
            else if (force)
            {
                peakSend->addOrDiscard(peak);
                hasPendingPeak = false;
            }
        }
    }
}

void History::bufferNadir(bool force)
{
    if (hasPendingNadir)
    {
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            bool buffered = nadirSend->addIfAvailable(nadir);
            if (buffered)
            {
                hasPendingNadir = false;
            }
            else if (force)
            {
                nadirSend->addOrDiscard(nadir);
                hasPendingNadir = false;
            }
        }
    }
}

void History::recordRssiChange(int delta)
{
  // clamp to prevent overflow
  prevRssiChange = constrain(delta, -127, 127);
}

bool History::canSendPeakNext()
{
  return peakSend->isEmpty() && (nadirSend->isEmpty() || (peakSend->first().firstTime < nadirSend->first().firstTime));
}

bool History::canSendNadirNext()
{
  return !nadirSend->isEmpty() && (peakSend->isEmpty() || (nadirSend->first().firstTime < peakSend->first().firstTime));
}

void History::checkForPeak()
{
  if (prevRssiChange >= 0 && isPeakValid(peak))
  {  // was rising or unchanged
      // declare a new peak
      hasPendingPeak = true;
  }
}

void History::checkForNadir()
{
  if (prevRssiChange <= 0 && isNadirValid(nadir))
  {  // was falling or unchanged
      // declare a new nadir
      hasPendingNadir = true;
  }
}

void History::reset()
{
    invalidatePeak(peak);
    hasPendingPeak = false;
    peakSend->clear();
    invalidateNadir(nadir);
    hasPendingNadir = false;
    nadirSend->clear();
    prevRssiChange = 0;
}
