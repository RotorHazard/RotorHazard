#include "config.h"
#include "RssiNode.h"

RssiNode RssiNode::rssiNodeArray[MULTI_RHNODE_MAX];
uint8_t RssiNode::multiRssiNodeCount = 1;
mtime_t RssiNode::lastRX5808BusTimeMs = 0;

RssiNode::RssiNode()
{
    filter = &defaultFilter;
    history = { {0, 0, 0}, false, &defaultPeakSendBuffer,
                {MAX_RSSI, 0, 0}, false, &defaultNadirSendBuffer, 0 };
}

void RssiNode::initRx5808Pins(int nIdx)
{
    nodeIndex = nIdx;
#if STM32_MODE_FLAG
    rx5808DataPin = PB3;  //DATA (CH1) output line to (all) RX5808 modules
    rx5808ClkPin = PB4;   //CLK (CH3) output line to (all) RX5808 modules
    rx5808SelPin = rx5808SelPinForNodeIndex(nIdx);  //SEL (CH2) output line to RX5808 module
    rssiInputPin = rssiInputPinForNodeIndex(nIdx);  //RSSI input from RX5808
#else
    rx5808DataPin = RX5808_DATA_PIN;  //DATA (CH1) output line to RX5808 module
    rx5808SelPin = RX5808_SEL_PIN;    //SEL (CH2) output line to RX5808 module
    rx5808ClkPin = RX5808_CLK_PIN;    //CLK (CH3) output line to RX5808 module
    rssiInputPin = RSSI_INPUT_PIN;    //RSSI input from RX5808
#endif
    pinMode(rx5808DataPin, OUTPUT);   //setup RX5808 pins
    pinMode(rx5808SelPin, OUTPUT);
    pinMode(rx5808ClkPin, OUTPUT);
    digitalWrite(rx5808SelPin, HIGH);
    digitalWrite(rx5808ClkPin, LOW);
    digitalWrite(rx5808DataPin, LOW);
}

// Initialize and set frequency on RX5808 module
void RssiNode::initRxModule()
{
    resetRxModule();
    setRxModuleToFreq(settings.vtxFreq);
}

// Set frequency on RX5808 module to given value
void RssiNode::setRxModuleToFreq(uint16_t vtxFreq)
{
    // check if enough time has elapsed since last set freq
    mtime_t timeVal = millis() - lastRX5808BusTimeMs;
    if(timeVal < RX5808_MIN_BUSTIME)
        delay(RX5808_MIN_BUSTIME - timeVal);  // wait until after-bus-delay time is fulfilled

    if (settings.vtxFreq == 1111) // frequency value to power down rx module
    {
        powerDownRxModule();
        rxPoweredDown = true;
        return;
    }
    if (rxPoweredDown)
    {
        resetRxModule();
        rxPoweredDown = false;
    }

    // Get the hex value to send to the rx module
    uint16_t vtxHex = freqMhzToRegVal(vtxFreq);

    // Channel data from the lookup table, 20 bytes of register data are sent, but the
    // MSB 4 bits are zeros register address = 0x1, write, data0-15=vtxHex data15-19=0x0
    rx5808SerialEnableHigh();
    rx5808SerialEnableLow();

    rx5808SerialSendBit1();  // Register 0x1
    rx5808SerialSendBit0();
    rx5808SerialSendBit0();
    rx5808SerialSendBit0();

    rx5808SerialSendBit1();  // Write to register

    // D0-D15, note: loop runs backwards as more efficent on AVR
    uint8_t i;
    for (i = 16; i > 0; i--)
    {
        if (vtxHex & 0x1)
        {  // Is bit high or low?
            rx5808SerialSendBit1();
        }
        else
        {
            rx5808SerialSendBit0();
        }
        vtxHex >>= 1;  // Shift bits along to check the next one
    }

    for (i = 4; i > 0; i--)  // Remaining D16-D19
        rx5808SerialSendBit0();

    rx5808SerialEnableHigh();  // Finished clocking data in
    delay(2);

    digitalWrite(rx5808ClkPin, LOW);
    digitalWrite(rx5808DataPin, LOW);

    recentSetFreqFlag = true;  // indicate need to wait RX5808_MIN_TUNETIME before reading RSSI
    lastRX5808BusTimeMs = lastSetFreqTimeMs = millis();  // mark time of last tune of RX5808 to freq
}

// Read the RSSI value for the current channel
rssi_t RssiNode::rssiRead()
{
    if (recentSetFreqFlag)
    {  // check if RSSI is stable after tune
        mtime_t timeVal = millis() - lastSetFreqTimeMs;
        if(timeVal < RX5808_MIN_TUNETIME)
            delay(RX5808_MIN_TUNETIME - timeVal);  // wait until after-tune-delay time is fulfilled
        recentSetFreqFlag = false;  // don't need to check again until next freq change
    }

    // reads 5V value as 0-1023, RX5808 is 3.3V powered so RSSI pin will never output the full range
    int raw = analogRead(rssiInputPin);
    // clamp upper range to fit scaling
    if (raw > 0x01FF)
        raw = 0x01FF;
    // rescale to fit into a byte and remove some jitter
    return raw >> 1;
}

void RssiNode::rx5808SerialSendBit1()
{
    digitalWrite(rx5808DataPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(rx5808ClkPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(rx5808ClkPin, LOW);
    delayMicroseconds(300);
}

void RssiNode::rx5808SerialSendBit0()
{
    digitalWrite(rx5808DataPin, LOW);
    delayMicroseconds(300);
    digitalWrite(rx5808ClkPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(rx5808ClkPin, LOW);
    delayMicroseconds(300);
}

void RssiNode::rx5808SerialEnableLow()
{
    digitalWrite(rx5808SelPin, LOW);
    delayMicroseconds(200);
}

void RssiNode::rx5808SerialEnableHigh()
{
    digitalWrite(rx5808SelPin, HIGH);
    delayMicroseconds(200);
}

// Reset rx5808 module to wake up from power down
void RssiNode::resetRxModule()
{
    rx5808SerialEnableHigh();
    rx5808SerialEnableLow();

    rx5808SerialSendBit1();  // Register 0xF
    rx5808SerialSendBit1();
    rx5808SerialSendBit1();
    rx5808SerialSendBit1();

    rx5808SerialSendBit1();  // Write to register

    for (uint8_t i = 20; i > 0; i--)
        rx5808SerialSendBit0();

    rx5808SerialEnableHigh();  // Finished clocking data in

    setupRxModule();
}

// Set power options on the rx5808 module
void RssiNode::setRxModulePower(uint32_t options)
{
    rx5808SerialEnableHigh();
    rx5808SerialEnableLow();

    rx5808SerialSendBit0();  // Register 0xA
    rx5808SerialSendBit1();
    rx5808SerialSendBit0();
    rx5808SerialSendBit1();

    rx5808SerialSendBit1();  // Write to register

    for (uint8_t i = 20; i > 0; i--)
    {
        if (options & 0x1)
        {  // Is bit high or low?
            rx5808SerialSendBit1();
        }
        else
        {
            rx5808SerialSendBit0();
        }
        options >>= 1;  // Shift bits along to check the next one
    }

    rx5808SerialEnableHigh();  // Finished clocking data in

    digitalWrite(RX5808_DATA_PIN, LOW);
}

// Power down rx5808 module
void RssiNode::powerDownRxModule()
{
    setRxModulePower(0b11111111111111111111);
}

// Set up rx5808 module (disabling unused features to save some power)
void RssiNode::setupRxModule()
{
    setRxModulePower(0b11010000110111110011);
}

// Calculate rx5808 register hex value for given frequency in MHz
uint16_t RssiNode::freqMhzToRegVal(uint16_t freqInMhz)
{
    uint16_t tf, N, A;
    tf = (freqInMhz - 479) / 2;
    N = tf / 32;
    A = tf % 32;
    return (N << (uint16_t)7) + A;
}


void RssiNode::rssiSetFilter(Filter<rssi_t> *f)
{
    filter = f;
}

void RssiNode::rssiSetSendBuffers(SendBuffer<Extremum> *peak, SendBuffer<Extremum> *nadir)
{
    history.peakSend = peak;
    history.nadirSend = nadir;
}

void RssiNode::rssiInit()
{
    state.lastloopMicros = micros();
}

bool RssiNode::rssiStateValid()
{
    return state.nodeRssiNadir <= state.rssi && state.rssi <= state.nodeRssiPeak;
}

void RssiNode::rssiStateReset()
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

void RssiNode::bufferHistoricPeak(bool force)
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

void RssiNode::bufferHistoricNadir(bool force)
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

void RssiNode::initExtremum(Extremum *e)
{
    e->rssi = state.rssi;
    e->firstTime = state.rssiTimestamp;
    e->duration = 0;
}

bool RssiNode::rssiProcess(mtime_t millis)
{
    filter->addRawValue(millis, rssiRead());

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
            if (state.rssi < state.passRssiNadir)
                state.passRssiNadir = state.rssi;
        }
    }

    // Calculate the time it takes to run the main loop
    utime_t loopMicros = micros();
    state.loopTimeMicros = loopMicros - state.lastloopMicros;
    state.lastloopMicros = loopMicros;

    return state.crossing;
}

// Function called when crossing ends (by RSSI or I2C command)
void RssiNode::rssiEndCrossing()
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


#if STM32_MODE_FLAG

int RssiNode::rx5808SelPinForNodeIndex(int nIdx)
{
    switch (nIdx)
    {
        case 1:
            return PB7;
        case 2:
            return PB8;
        case 3:
            return PB9;
        case 4:
            return PB12;
        case 5:
            return PB13;
        case 6:
            return PB14;
        case 7:
            return PB15;
        default:
            return PB6;
    }
}

int RssiNode::rssiInputPinForNodeIndex(int nIdx)
{
    switch (nIdx)
    {
        case 1:
            return A1;
        case 2:
            return A2;
        case 3:
            return A3;
        case 4:
            return A4;
        case 5:
            return A5;
        case 6:
            return A6;
        case 7:
            return A7;
        default:
            return A0;
    }
}

#endif
