#include "config.h"
#include "microclock.h"
#include "rssi.h"
#include "commands.h"

extern void handleStatusMessage(uint8_t msgType, uint8_t data);

constexpr uint_fast16_t RSSI_HISTORY_PAYLOAD_SIZE = 16;
constexpr uint_fast8_t SCAN_HISTORY_PAYLOAD_COUNT = 3;
constexpr uint_fast8_t SCAN_HISTORY_PAYLOAD_SIZE = SCAN_HISTORY_PAYLOAD_COUNT*sizeof(FreqRssi);

uint8_t volatile cmdStatusFlags = NO_STATUS;
uint_fast8_t volatile cmdRssiNodeIndex = 0;

int_fast8_t Message::getPayloadSize() const
{
    int_fast8_t size;
    switch (command)
    {
        case WRITE_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
        case WRITE_MODE:
        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
        case RESET_PAIRED_NODE:  // reset paired node for ISP
        case WRITE_CURNODE_INDEX:  // index of current node for this processor
        case JUMP_TO_BOOTLOADER:  // jump to bootloader for flash update
            size = 1;
            break;

        case WRITE_FREQUENCY:
        case SEND_STATUS_MESSAGE:
            size = 2;
            break;

        default:  // invalid command
            LOG_ERROR("Invalid write command: ", command, HEX);
            size = -1;
    }
    return size;
}

// Generic IO write command handler
void Message::handleWriteCommand(CommSource src)
{
    buffer.flipForRead();
    bool activityFlag = true;
    uint8_t statusFlags = cmdStatusFlags; // non-volatile copy

    switch (command)
    {
        case WRITE_FREQUENCY:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                freq_t freq = buffer.read16();
                if (freq >= MIN_FREQ && freq <= MAX_FREQ)
                {
                    RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                    Settings& settings = rssiNode.getSettings();
                    if (freq != settings.vtxFreq)
                    {
                        settings.vtxFreq = freq;
                        rssiNode.pendingOps |= FREQ_CHANGED;
                    }
                    rssiNode.pendingOps |= FREQ_SET;
                }
            }
            break;

        case WRITE_MODE:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                uint8_t mode = buffer.read8();
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                setMode(rssiNode, (Mode)mode);
            }
            break;

        case WRITE_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                rssi_t rssiVal = ioBufferReadRssi(buffer);
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                Settings& settings = rssiNode.getSettings();
                if (rssiVal != settings.enterAtLevel)
                {
                    settings.enterAtLevel = rssiVal;
                    hardware.storeEnterAtLevel(settings.enterAtLevel);
                }
            }
            break;

        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                rssi_t rssiVal = ioBufferReadRssi(buffer);
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                Settings& settings = rssiNode.getSettings();
                if (rssiVal != settings.exitAtLevel)
                {
                    settings.exitAtLevel = rssiVal;
                    hardware.storeExitAtLevel(settings.exitAtLevel);
                }
            }
            break;

        case WRITE_CURNODE_INDEX:  // index of current node for this processor
            {
                uint8_t idx = buffer.read8();
                if (idx < rssiRxs.getCount()) {
                    cmdRssiNodeIndex = idx;
                }
            }
            break;

        case SEND_STATUS_MESSAGE:  // status message sent from server to node
            {
                uint16_t msg = buffer.read16();  // upper byte is message type, lower byte is data
                handleStatusMessage((uint8_t)(msg >> 8), (uint8_t)(msg & 0x00FF));
            }
            break;

        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                rssiNode.endCrossing();
            }
            break;

        case RESET_PAIRED_NODE:  // reset paired node for ISP
            {
                uint8_t pinState = buffer.read8();
                hardware.resetPairedNode(pinState);
            }
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
        statusFlags |= COMM_ACTIVITY;
        if (src == SERIAL_SOURCE) {
            statusFlags |= SERIAL_CMD_MSG;
        }
    }
    cmdStatusFlags = statusFlags; // update volatile

    command = INVALID_COMMAND;  // Clear previous command
}

template <size_t N,size_t T> void ioBufferWriteExtremum(Buffer<N,T>& buf, const Extremum& e, mtime_t now)
{
    ioBufferWriteRssi(buf, e.rssi);
    buf.write16(toDuration(now - e.firstTime));
    buf.write16(e.duration);
}

void Message::setMode(RssiNode& rssiNode, Mode mode) const
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
            rssiNode.pendingOps |= FREQ_CHANGED;
            rssiNode.pendingOps |= FREQ_SET;
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
void Message::handleReadCommand(CommSource src)
{
    buffer.flipForWrite();
    bool activityFlag = true;
    uint8_t statusFlags = cmdStatusFlags; // non-volatile copy

    switch (command)
    {
        case READ_ADDRESS:
            buffer.write8(hardware.getAddress());
            break;

        case READ_FREQUENCY:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                Settings& settings = rssiNode.getSettings();
                buffer.write16(settings.vtxFreq);
            } else {
                buffer.write16(0xFFFF);
            }
            break;

        case READ_MODE:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                Settings& settings = rssiNode.getSettings();
                buffer.write8(settings.mode);
            } else {
                buffer.write8(0xFF);
            }
            break;

        case READ_LAP_STATS:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                mtime_t timeNowVal = usclock.millis();
                handleReadLapPassStats(rssiNode, timeNowVal);
                handleReadLapExtremums(rssiNode, timeNowVal);
                statusFlags |= POLLING;
            }
            break;

        case READ_LAP_PASS_STATS:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                handleReadLapPassStats(rssiNode, usclock.millis());
                statusFlags |= POLLING;
            }
            break;

        case READ_LAP_EXTREMUMS:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                handleReadLapExtremums(rssiNode, usclock.millis());
            }
            break;

        case READ_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                Settings& settings = rssiNode.getSettings();
                ioBufferWriteRssi(buffer, settings.enterAtLevel);
            } else {
                ioBufferWriteRssi(buffer, MAX_RSSI);
            }
            break;

        case READ_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                Settings& settings = rssiNode.getSettings();
                ioBufferWriteRssi(buffer, settings.exitAtLevel);
            } else {
                ioBufferWriteRssi(buffer, MAX_RSSI);
            }
            break;

        case READ_REVISION_CODE:  // reply with NODE_API_LEVEL and verification value
            buffer.write16((0x25 << 8) + (uint16_t)NODE_API_LEVEL);
            break;

        case READ_NODE_RSSI_PEAK:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                State& state = rssiNode.getState();
                ioBufferWriteRssi(buffer, state.nodeRssiPeak);
            } else {
                ioBufferWriteRssi(buffer, 0);
            }
            break;

        case READ_NODE_RSSI_NADIR:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                State& state = rssiNode.getState();
                ioBufferWriteRssi(buffer, state.nodeRssiNadir);
            } else {
                ioBufferWriteRssi(buffer, MAX_RSSI);
            }
            break;

        case READ_NODE_RSSI_HISTORY:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                handleReadRssiHistory(rssiNode);
                statusFlags |= POLLING;
            }
            break;

        case READ_NODE_SCAN_HISTORY:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                RssiNode& rssiNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
                handleReadScanHistory(rssiNode);
                statusFlags |= POLLING;
            }
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
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                buffer.write8(cmdRssiNodeIndex);
            } else {
                buffer.write8(0xFF);
            }
            break;

        case READ_NODE_SLOTIDX:
            if (cmdRssiNodeIndex < rssiRxs.getCount())
            {
                buffer.write8(rssiRxs.getSlotIndex(cmdRssiNodeIndex));
            } else {
                buffer.write8(0xFF);
            }
            break;

        case READ_FW_VERSION:
            buffer.writeText("B1.3");
            break;

        case READ_FW_BUILDDATE:
            buffer.writeText(__DATE__);
            break;

        case READ_FW_BUILDTIME:
            buffer.writeText(__TIME__);
            break;

        case READ_FW_PROCTYPE:
            buffer.writeText(hardware.getProcessorType());
            break;

        default:  // If an invalid command is sent, write nothing back, master must react
            LOG_ERROR("Invalid read command: ", command, HEX);
            activityFlag = false;  // not valid activity
    }

    // indicate communications activity detected
    if (activityFlag)
    {
        statusFlags |= COMM_ACTIVITY;
        if (src == SERIAL_SOURCE) {
            statusFlags |= SERIAL_CMD_MSG;
        }
    }
    cmdStatusFlags = statusFlags; // update volatile

    if (!buffer.isEmpty())
    {
        buffer.writeChecksum();
    }

    command = INVALID_COMMAND;  // Clear previous command
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

void handleStreamEvent(Stream& stream, Message& msg, CommSource src)
{
    uint8_t nextByte = stream.read();
    if (msg.buffer.size == 0)
    {
        // new command
        msg.command = (Command) nextByte;
        if (msg.isWriteCommand())
        {  // Commands > 0x50 are writes TO this slave
            int_fast8_t expectedSize = msg.getPayloadSize();
            if (expectedSize > 0)
            {
                msg.buffer.index = 0;
                msg.buffer.size = expectedSize + 1;  // include checksum byte
            }
        }
        else
        {
            msg.handleReadCommand(src);
            sendReadCommandResponse(stream, msg);
        }
    }
    else
    {
        // existing command
        msg.buffer.data[msg.buffer.index++] = nextByte;
        validateAndProcessWriteCommand(msg, src);
    }
}

void sendReadCommandResponse(Stream& stream, Message& msg) {
    // if there is pending data, send it
    if (msg.buffer.size > 0) {
        stream.write(msg.buffer.data, msg.buffer.size);
        msg.buffer.size = 0;
    }
}

void validateAndProcessWriteCommand(Message& msg, CommSource src) {
    if (msg.buffer.index == msg.buffer.size)
    {
        uint8_t checksum = msg.buffer.calculateChecksum(msg.buffer.size - 1);
        if (msg.buffer.data[msg.buffer.size - 1] == checksum)
        {
            msg.handleWriteCommand(src);
        }
        else
        {
            LOG_ERROR("Invalid checksum", checksum, HEX);
        }
        msg.buffer.size = 0;
    }
}
