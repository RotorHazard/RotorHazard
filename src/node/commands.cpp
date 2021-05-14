#include "config.h"
#include "microclock.h"
#include "rssi.h"
#include "commands.h"

constexpr uint_fast16_t RSSI_HISTORY_PAYLOAD_SIZE = 16;
constexpr uint_fast8_t SCAN_HISTORY_PAYLOAD_COUNT = 3;
constexpr uint_fast8_t SCAN_HISTORY_PAYLOAD_SIZE = SCAN_HISTORY_PAYLOAD_COUNT*sizeof(FreqRssi);

uint8_t volatile cmdStatusFlags = 0;
uint_fast8_t volatile cmdRssiNodeIndex = 0;

uint8_t Message::getPayloadSize()
{
    uint8_t size;
    switch (command)
    {
        case WRITE_FREQUENCY:
            size = 2;
            break;

        case WRITE_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            size = 1;
            break;

        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            size = 1;
            break;

        case WRITE_MODE:
            size = 1;
            break;

        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
            size = 1;
            break;

        case RESET_PAIRED_NODE:  // reset paired node for ISP
            size = 1;
            break;

        case WRITE_CURNODE_INDEX:  // index of current node for this processor
            size = 1;
            break;

        case JUMP_TO_BOOTLOADER:  // jump to bootloader for flash update
            size = 1;
            break;

        default:  // invalid command
            LOG_ERROR("Invalid write command: ", command, HEX);
            size = -1;
    }
    return size;
}

// Generic IO write command handler
void Message::handleWriteCommand(bool serialFlag)
{
    uint8_t u8val;
    uint16_t u16val;
    rssi_t rssiVal;

    buffer.flipForRead();
    bool activityFlag = true;

    RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
    Settings& settings = rssiNode.getSettings();

    switch (command)
    {
        case WRITE_FREQUENCY:
            u16val = buffer.read16();
            if (u16val >= MIN_FREQ && u16val <= MAX_FREQ)
            {
                if (u16val != settings.vtxFreq)
                {
                    settings.vtxFreq = u16val;
                    rssiNode.cmdPendingOps |= FREQ_CHANGED;
                }
                rssiNode.cmdPendingOps |= FREQ_SET;
            }
            break;

        case WRITE_MODE:
            u8val = buffer.read8();
            setMode(rssiNode, (Mode)u8val);
            break;

        case WRITE_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            rssiVal = ioBufferReadRssi(buffer);
            if (rssiVal != settings.enterAtLevel)
            {
                settings.enterAtLevel = rssiVal;
                rssiNode.cmdPendingOps |= ENTERAT_CHANGED;
            }
            break;

        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            rssiVal = ioBufferReadRssi(buffer);
            if (rssiVal != settings.exitAtLevel)
            {
                settings.exitAtLevel = rssiVal;
                rssiNode.cmdPendingOps |= EXITAT_CHANGED;
            }
            break;

        case WRITE_CURNODE_INDEX:  // index of current node for this processor
            u8val = buffer.read8();
            if (u8val < rssiRxs.getCount()) {
              cmdRssiNodeIndex = u8val;
            }
            break;

        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
            rssiNode.endCrossing();
            break;

        case RESET_PAIRED_NODE:  // reset paired node for ISP
            u8val = buffer.read8();
            hardware.resetPairedNode(u8val);
            break;

        case JUMP_TO_BOOTLOADER:  // jump to bootloader for flash update
            hardware.doJumpToBootloader();
            break;

        default:
            LOG_ERROR("Invalid write command: ", command, HEX);
            activityFlag = false;  // not valid activity
    }

    // indicate communications activity detected
    if (activityFlag)
    {
        cmdStatusFlags |= COMM_ACTIVITY;
        if (serialFlag)
            cmdStatusFlags |= SERIAL_CMD_MSG;
    }

    command = 0;  // Clear previous command
}

template <size_t N> void ioBufferWriteExtremum(Buffer<N>& buf, const Extremum& e, mtime_t now)
{
    ioBufferWriteRssi(buf, e.rssi);
    buf.write16(toDuration(now - e.firstTime));
    buf.write16(e.duration);
}

void Message::setMode(RssiNode& rssiNode, Mode mode)
{
    Settings& settings = rssiNode.getSettings();
    switch (mode) {
        case TIMER:
            rssiNode.setFilter(&(rssiNode.defaultFilter));
            settings.mode = mode;
            break;
        case SCANNER:
#ifdef SCAN_HISTORY
            rssiNode.scanHistory.clear();
            rssiNode.setFilter(&(rssiNode.medianFilter));
            settings.vtxFreq = MIN_SCAN_FREQ;
            cmdStatusFlags |= FREQ_CHANGED;
            cmdStatusFlags |= FREQ_SET;
            settings.mode = mode;
#endif
            break;
        case RAW:
#ifdef RSSI_HISTORY
            rssiNode.rssiHistory.clear();
            rssiNode.setFilter(&(rssiNode.noFilter));
            settings.mode = mode;
#endif
            break;
    }
    rssiNode.resetState(usclock.millis());
}

// Generic IO read command handler
void Message::handleReadCommand(bool serialFlag)
{
    buffer.flipForWrite();
    bool activityFlag = true;

    RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
    Settings& settings = rssiNode.getSettings();
    State& state = rssiNode.getState();

    switch (command)
    {
        case READ_ADDRESS:
            buffer.write8(hardware.getAddress());
            break;

        case READ_FREQUENCY:
            buffer.write16(settings.vtxFreq);
            break;

        case READ_MODE:
            buffer.write8(settings.mode);
            break;

        case READ_LAP_STATS:
            {
            mtime_t timeNowVal = usclock.millis();
            handleReadLapPassStats(rssiNode, timeNowVal);
            handleReadLapExtremums(rssiNode, timeNowVal);
            cmdStatusFlags |= POLLING;
            }
            break;

        case READ_LAP_PASS_STATS:
            handleReadLapPassStats(rssiNode, usclock.millis());
            cmdStatusFlags |= POLLING;
            break;

        case READ_LAP_EXTREMUMS:
            handleReadLapExtremums(rssiNode, usclock.millis());
            break;

        case READ_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            ioBufferWriteRssi(buffer, settings.enterAtLevel);
            break;

        case READ_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            ioBufferWriteRssi(buffer, settings.exitAtLevel);
            break;

        case READ_REVISION_CODE:  // reply with NODE_API_LEVEL and verification value
            buffer.write16((0x25 << 8) + (uint16_t)NODE_API_LEVEL);
            break;

        case READ_NODE_RSSI_PEAK:
            ioBufferWriteRssi(buffer, state.nodeRssiPeak);
            break;

        case READ_NODE_RSSI_NADIR:
            ioBufferWriteRssi(buffer, state.nodeRssiNadir);
            break;

        case READ_NODE_RSSI_HISTORY:
            handleReadRssiHistory(rssiNode);
            cmdStatusFlags |= POLLING;
            break;

        case READ_NODE_SCAN_HISTORY:
            handleReadScanHistory(rssiNode);
            cmdStatusFlags |= POLLING;
            break;

        case READ_TIME_MILLIS:
            buffer.write32(usclock.millis());
            break;

        case READ_RHFEAT_FLAGS:   // reply with feature flags value
            buffer.write16(hardware.getFeatureFlags());
            break;

        case READ_MULTINODE_COUNT:
            buffer.write8(rssiRxs.getCount());
            break;

        case READ_CURNODE_INDEX:
            buffer.write8(cmdRssiNodeIndex);
            break;

        case READ_NODE_SLOTIDX:
            buffer.write8(rssiRxs.getSlotIndex(cmdRssiNodeIndex));
            break;

        default:  // If an invalid command is sent, write nothing back, master must react
            LOG_ERROR("Invalid read command: ", command, HEX);
            activityFlag = false;  // not valid activity
    }

    // indicate communications activity detected
    if (activityFlag)
    {
        cmdStatusFlags |= COMM_ACTIVITY;
        if (serialFlag) {
            cmdStatusFlags |= SERIAL_CMD_MSG;
        }
    }

    if (!buffer.isEmpty())
    {
        buffer.writeChecksum();
    }

    command = 0;  // Clear previous command
}

void Message::handleReadLapPassStats(RssiNode& rssiNode, mtime_t timeNowVal)
{
    State& state = rssiNode.getState();
    LastPass& lastPass = rssiNode.getLastPass();
    buffer.write8(lastPass.lap);
    buffer.write16(toDuration(timeNowVal - lastPass.timestamp));  // ms since lap
    ioBufferWriteRssi(buffer, state.rssi);
    ioBufferWriteRssi(buffer, state.nodeRssiPeak);
    ioBufferWriteRssi(buffer, lastPass.rssiPeak);  // RSSI peak for last lap pass
    buffer.write16(toDuration(state.loopTimeMicros));
}

void Message::handleReadLapExtremums(RssiNode& rssiNode, mtime_t timeNowVal)
{
    State& state = rssiNode.getState();
    LastPass& lastPass = rssiNode.getLastPass();
    History& history = rssiNode.getHistory();
    // set flag if 'crossing' in progress
    uint8_t flags = rssiNode.isCrossing() ? (uint8_t)LAPSTATS_FLAG_CROSSING : (uint8_t)0;
    ExtremumType extremumType = history.nextToSendType();
    if (extremumType == PEAK)
    {
        flags |= LAPSTATS_FLAG_PEAK;
    }
    buffer.write8(flags);
    ioBufferWriteRssi(buffer, lastPass.rssiNadir);  // lowest rssi since end of last pass
    ioBufferWriteRssi(buffer, state.nodeRssiNadir);

    switch(extremumType) {
        case PEAK:
            // send peak
            ioBufferWriteExtremum(buffer, history.popNextToSend(), timeNowVal);
            break;
        case NADIR:
            // send nadir
            ioBufferWriteExtremum(buffer, history.popNextToSend(), timeNowVal);
            break;
        default:
            ioBufferWriteRssi(buffer, 0);
            buffer.write16(0);
            buffer.write16(0);
    }
}

void Message::handleReadRssiHistory(RssiNode& rssiNode)
{
    int i = 0;
#ifdef RSSI_HISTORY
    CircularBuffer<rssi_t,RSSI_HISTORY_SIZE>& rssiHistory = rssiNode.rssiHistory;
    const uint_fast16_t n = min(rssiHistory.size(), RSSI_HISTORY_PAYLOAD_SIZE);
    for (; i<n; i++) {
        ioBufferWriteRssi(buffer, rssiHistory.shift());
    }
    if (i<RSSI_HISTORY_PAYLOAD_SIZE && rssiNode.rssiHistoryComplete) {
        ioBufferWriteRssi(buffer, MAX_RSSI);
        i++;
        rssiNode.rssiHistoryComplete = false;
    }
#endif
    for (; i<RSSI_HISTORY_PAYLOAD_SIZE; i++) {
        ioBufferWriteRssi(buffer, 0);
    }
}

void Message::handleReadScanHistory(RssiNode& rssiNode)
{
    int i = 0;
#ifdef SCAN_HISTORY
    CircularBuffer<FreqRssi,SCAN_HISTORY_SIZE>& scanHistory = rssiNode.scanHistory;
    const uint_fast8_t n = min(scanHistory.size(), SCAN_HISTORY_PAYLOAD_COUNT);
    for (; i<n; i++) {
        ioBufferWriteFreqRssi(buffer, scanHistory.shift());
    }
#endif
    const FreqRssi f_r = {0, 0};
    for (; i<SCAN_HISTORY_PAYLOAD_COUNT; i++) {
        ioBufferWriteFreqRssi(buffer, f_r);
    }
}

void handleStreamEvent(Stream& stream, Message& msg)
{
    uint8_t nextByte = stream.read();
    if (msg.buffer.size == 0)
    {
        // new command
        msg.command = nextByte;
        if (msg.command > 0x50)
        {  // Commands > 0x50 are writes TO this slave
            uint8_t expectedSize = msg.getPayloadSize();
            if (expectedSize > 0)
            {
                msg.buffer.index = 0;
                msg.buffer.size = expectedSize + 1;  // include checksum byte
            }
        }
        else
        {
            msg.handleReadCommand(true);

            if (msg.buffer.size > 0)
            {  // If there is pending data, send it
                stream.write(msg.buffer.data, msg.buffer.size);
                msg.buffer.size = 0;
            }
        }
    }
    else
    {
        // existing command
        msg.buffer.data[msg.buffer.index++] = nextByte;
        if (msg.buffer.index == msg.buffer.size)
        {
            uint8_t checksum = msg.buffer.calculateChecksum(msg.buffer.size - 1);
            if (msg.buffer.data[msg.buffer.size - 1] == checksum)
            {
                msg.handleWriteCommand(true);
            }
            else
            {
                LOG_ERROR("Invalid checksum", checksum);
            }
            msg.buffer.size = 0;
        }
    }
}
