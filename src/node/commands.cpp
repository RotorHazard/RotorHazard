#include "config.h"
#include "clock.h"
#include "rssi.h"
#include "commands.h"

#ifdef __TEST__
  static uint8_t i2cSlaveAddress = 0x08;
#else
  extern uint8_t i2cSlaveAddress;
#endif

#if STM32_MODE_FLAG
  void doJumpToBootloader();
#endif

uint8_t cmdStatusFlags = 0;
uint8_t cmdRssiNodeIndex = 0;

byte Message::getPayloadSize()
{
    byte size;
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

// Node reset for ISP; resets other node wired to this node's reset pin
void resetPairedNode(int pinState)
{
#if !STM32_MODE_FLAG
    if (pinState)
    {
        pinMode(NODE_RESET_PIN, INPUT_PULLUP);
    }
    else
    {
        pinMode(NODE_RESET_PIN, OUTPUT);
        digitalWrite(NODE_RESET_PIN, LOW);
    }
#endif
}

// Generic IO write command handler
void Message::handleWriteCommand(bool serialFlag)
{
    uint8_t u8val;
    uint16_t u16val;
    rssi_t rssiVal;

    buffer.flipForRead();
    bool activityFlag = true;

    RssiNode& rssiNode = rssiRxs->getRssiNode(cmdRssiNodeIndex);
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
                    cmdStatusFlags |= FREQ_CHANGED;
                }
                cmdStatusFlags |= FREQ_SET;
            }
            break;

        case WRITE_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            rssiVal = ioBufferReadRssi(buffer);
            if (rssiVal != settings.enterAtLevel)
            {
                settings.enterAtLevel = rssiVal;
                cmdStatusFlags |= ENTERAT_CHANGED;
            }
            break;

        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            rssiVal = ioBufferReadRssi(buffer);
            if (rssiVal != settings.exitAtLevel)
            {
                settings.exitAtLevel = rssiVal;
                cmdStatusFlags |= EXITAT_CHANGED;
            }
            break;

        case WRITE_CURNODE_INDEX:  // index of current node for this processor
            u8val = buffer.read8();
            if (u8val < rssiRxs->getCount() && u8val != cmdRssiNodeIndex) {
              cmdRssiNodeIndex = u8val;
            }
            break;

        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
            rssiNode.endCrossing();
            break;

        case RESET_PAIRED_NODE:  // reset paired node for ISP
            u8val = buffer.read8();
            resetPairedNode(u8val);
            break;

        case JUMP_TO_BOOTLOADER:  // jump to bootloader for flash update
#if STM32_MODE_FLAG
            doJumpToBootloader();
#endif
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

void ioBufferWriteExtremum(Buffer& buf, const Extremum& e, mtime_t now)
{
    ioBufferWriteRssi(buf, e.rssi);
    buf.write16(uint16_t(now - e.firstTime));
    buf.write16(e.duration);
}

// Generic IO read command handler
void Message::handleReadCommand(bool serialFlag)
{
    buffer.flipForWrite();
    bool activityFlag = true;

    RssiNode& rssiNode = rssiRxs->getRssiNode(cmdRssiNodeIndex);
    Settings& settings = rssiNode.getSettings();
    State& state = rssiNode.getState();

    switch (command)
    {
        case READ_ADDRESS:
            buffer.write8(i2cSlaveAddress);
            break;

        case READ_FREQUENCY:
            buffer.write16(settings.vtxFreq);
            break;

        case READ_LAP_STATS:
            {
            mtime_t timeNowVal = usclock.millis();
            handleReadLapPassStats(rssiNode, timeNowVal);
            handleReadLapExtremums(rssiNode, timeNowVal);
            cmdStatusFlags |= LAPSTATS_READ;
            }
            break;

        case READ_LAP_PASS_STATS:
            handleReadLapPassStats(rssiNode, usclock.millis());
            cmdStatusFlags |= LAPSTATS_READ;
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
            buffer.write16((0x25 << 8) + NODE_API_LEVEL);
            break;

        case READ_NODE_RSSI_PEAK:
            ioBufferWriteRssi(buffer, state.nodeRssiPeak);
            break;

        case READ_NODE_RSSI_NADIR:
            ioBufferWriteRssi(buffer, state.nodeRssiNadir);
            break;

        case READ_TIME_MILLIS:
            buffer.write32(usclock.millis());
            break;

        case READ_RHFEAT_FLAGS:   // reply with feature flags value
            buffer.write16(RHFEAT_FLAGS_VALUE);
            break;

        case READ_MULTINODE_COUNT:
            buffer.write8(rssiRxs->getCount());
            break;

        case READ_CURNODE_INDEX:
            buffer.write8(cmdRssiNodeIndex);
            break;

        case READ_NODE_SLOTIDX:
            buffer.write8(rssiRxs->getSlotIndex(cmdRssiNodeIndex));
            break;

        default:  // If an invalid command is sent, write nothing back, master must react
            LOG_ERROR("Invalid read command: ", command, HEX);
            activityFlag = false;  // not valid activity
    }

    // indicate communications activity detected
    if (activityFlag)
    {
        cmdStatusFlags |= COMM_ACTIVITY;
        if (serialFlag)
            cmdStatusFlags |= SERIAL_CMD_MSG;
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
    buffer.write16(uint16_t(timeNowVal - lastPass.timestamp));  // ms since lap
    ioBufferWriteRssi(buffer, state.rssi);
    ioBufferWriteRssi(buffer, state.nodeRssiPeak);
    ioBufferWriteRssi(buffer, lastPass.rssiPeak);  // RSSI peak for last lap pass
    buffer.write16(uint16_t(state.loopTimeMicros));
}

void Message::handleReadLapExtremums(RssiNode& rssiNode, mtime_t timeNowVal)
{
    State& state = rssiNode.getState();
    LastPass& lastPass = rssiNode.getLastPass();
    History& history = rssiNode.getHistory();
    // set flag if 'crossing' in progress
    uint8_t flags = state.crossing ? (uint8_t)LAPSTATS_FLAG_CROSSING : (uint8_t)0;
    if (history.canSendPeakNext())
    {
        flags |= LAPSTATS_FLAG_PEAK;
    }
    buffer.write8(flags);
    ioBufferWriteRssi(buffer, lastPass.rssiNadir);  // lowest rssi since end of last pass
    ioBufferWriteRssi(buffer, state.nodeRssiNadir);

    if (history.canSendPeakNext())
    {
        // send peak
        ioBufferWriteExtremum(buffer, history.peakSend->first(), timeNowVal);
        history.peakSend->removeFirst();
    }
    else if (history.canSendNadirNext())
    {
        // send nadir
        ioBufferWriteExtremum(buffer, history.nadirSend->first(), timeNowVal);
        history.nadirSend->removeFirst();
    }
    else
    {
        ioBufferWriteRssi(buffer, 0);
        buffer.write16(0);
        buffer.write16(0);
    }
}
