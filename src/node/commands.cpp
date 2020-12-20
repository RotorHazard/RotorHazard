#include "config.h"
#include "RssiNode.h"
#include "commands.h"

#ifdef __TEST__
  static uint8_t i2cSlaveAddress = 0x08;
#else
#if !STM32_MODE_FLAG
  extern uint8_t i2cSlaveAddress;
#else
  void doJumpToBootloader();
#endif
#endif

uint8_t settingChangedFlags = 0;

RssiNode *cmdRssiNodePtr = &(RssiNode::rssiNodeArray[0]);  //current RssiNode for commands

RssiNode *getCmdRssiNodePtr()
{
    return cmdRssiNodePtr;
}

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
    if (pinState)
    {
        pinMode(NODE_RESET_PIN, INPUT_PULLUP);
    }
    else
    {
        pinMode(NODE_RESET_PIN, OUTPUT);
        digitalWrite(NODE_RESET_PIN, LOW);
    }
}

// Generic IO write command handler
void Message::handleWriteCommand(bool serialFlag)
{
    uint8_t u8val;
    uint16_t u16val;
    rssi_t rssiVal;
    uint8_t nIdx;

    buffer.flipForRead();
    bool actFlag = true;

    switch (command)
    {
        case WRITE_FREQUENCY:
            u16val = buffer.read16();
            if (u16val >= MIN_FREQ && u16val <= MAX_FREQ)
            {
                if (u16val != cmdRssiNodePtr->getVtxFreq())
                {
                    cmdRssiNodePtr->setVtxFreq(u16val);
                    settingChangedFlags |= FREQ_CHANGED;
#if STM32_MODE_FLAG
                    cmdRssiNodePtr->rssiStateReset();  // restart rssi peak tracking for node
#endif
                }
                settingChangedFlags |= FREQ_SET;
#if STM32_MODE_FLAG  // need to wait here for completion to avoid data overruns
                cmdRssiNodePtr->setRxModuleToFreq(u16val);
                cmdRssiNodePtr->setActivatedFlag(true);
#endif
            }
            break;

        case WRITE_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            rssiVal = ioBufferReadRssi(buffer);
            if (rssiVal != cmdRssiNodePtr->getEnterAtLevel())
            {
                cmdRssiNodePtr->setEnterAtLevel(rssiVal);
                settingChangedFlags |= ENTERAT_CHANGED;
            }
            break;

        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            rssiVal = ioBufferReadRssi(buffer);
            if (rssiVal != cmdRssiNodePtr->getExitAtLevel())
            {
                cmdRssiNodePtr->setExitAtLevel(rssiVal);
                settingChangedFlags |= EXITAT_CHANGED;
            }
            break;

        case WRITE_CURNODE_INDEX:  // index of current node for this processor
            nIdx = buffer.read8();
            if (nIdx < RssiNode::multiRssiNodeCount && nIdx != cmdRssiNodePtr->getNodeIndex())
                cmdRssiNodePtr = &(RssiNode::rssiNodeArray[nIdx]);
            break;

        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
            cmdRssiNodePtr->rssiEndCrossing();
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
            actFlag = false;  // not valid activity
    }

    // indicate communications activity detected
    if (actFlag)
    {
        settingChangedFlags |= COMM_ACTIVITY;
        if (serialFlag)
            settingChangedFlags |= SERIAL_CMD_MSG;
    }

    command = 0;  // Clear previous command
}

void ioBufferWriteExtremum(Buffer& buf, const Extremum& e, mtime_t now)
{
    ioBufferWriteRssi(buf, e.rssi);
    buf.write16(uint16_t(now - e.firstTime));
    buf.write16(uint16_t(now - e.firstTime - e.duration));
}

// Generic IO read command handler
void Message::handleReadCommand(bool serialFlag)
{
    buffer.flipForWrite();
    bool actFlag = true;

    switch (command)
    {
        case READ_ADDRESS:
#if !STM32_MODE_FLAG
            buffer.write8(i2cSlaveAddress);
#else
            buffer.write8((uint8_t)0);
#endif
            break;

        case READ_FREQUENCY:
            buffer.write16(cmdRssiNodePtr->getVtxFreq());
            break;

        case READ_LAP_STATS:  // deprecated; use READ_LAP_PASS_STATS and READ_LAP_EXTREMUMS
            {
                mtime_t timeNowVal = millis();
                handleReadLapPassStats(timeNowVal);
                handleReadLapExtremums(timeNowVal);
                settingChangedFlags |= LAPSTATS_READ;
            }
            break;

        case READ_LAP_PASS_STATS:
            handleReadLapPassStats(millis());
            settingChangedFlags |= LAPSTATS_READ;
            break;

        case READ_LAP_EXTREMUMS:
            handleReadLapExtremums(millis());
            break;

        case READ_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            ioBufferWriteRssi(buffer, cmdRssiNodePtr->getEnterAtLevel());
            break;

        case READ_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            ioBufferWriteRssi(buffer, cmdRssiNodePtr->getExitAtLevel());
            break;

        case READ_REVISION_CODE:  // reply with NODE_API_LEVEL and verification value
            buffer.write16((0x25 << 8) + NODE_API_LEVEL);
            break;

        case READ_NODE_RSSI_PEAK:
            ioBufferWriteRssi(buffer, cmdRssiNodePtr->getState().nodeRssiPeak);
            break;

        case READ_NODE_RSSI_NADIR:
            ioBufferWriteRssi(buffer, cmdRssiNodePtr->getState().nodeRssiNadir);
            break;

        case READ_TIME_MILLIS:
            buffer.write32(millis());
            break;

        case READ_RHFEAT_FLAGS:   // reply with feature flags value
            buffer.write16(RHFEAT_FLAGS_VALUE);
            break;

        case READ_MULTINODE_COUNT:
            buffer.write8(RssiNode::multiRssiNodeCount);
            break;

        case READ_CURNODE_INDEX:
            buffer.write8(cmdRssiNodePtr->getNodeIndex());
            break;

        default:  // If an invalid command is sent, write nothing back, master must react
            LOG_ERROR("Invalid read command: ", command, HEX);
            actFlag = false;  // not valid activity
    }

    // indicate communications activity detected
    if (actFlag)
    {
        settingChangedFlags |= COMM_ACTIVITY;
        if (serialFlag)
            settingChangedFlags |= SERIAL_CMD_MSG;
    }

    if (!buffer.isEmpty())
    {
        buffer.writeChecksum();
    }

    command = 0;  // Clear previous command
}

void Message::handleReadLapPassStats(mtime_t timeNowVal)
{
    buffer.write8(cmdRssiNodePtr->getLastPass().lap);
    buffer.write16(uint16_t(timeNowVal - cmdRssiNodePtr->getLastPass().timestamp));  // ms since lap
    ioBufferWriteRssi(buffer, cmdRssiNodePtr->getState().rssi);
    ioBufferWriteRssi(buffer, cmdRssiNodePtr->getState().nodeRssiPeak);
    ioBufferWriteRssi(buffer, cmdRssiNodePtr->getLastPass().rssiPeak);  // RSSI peak for last lap pass
    buffer.write16(uint16_t(cmdRssiNodePtr->getState().loopTimeMicros));
}

void Message::handleReadLapExtremums(mtime_t timeNowVal)
{
    // set flag if 'crossing' in progress
    uint8_t flags = cmdRssiNodePtr->getState().crossing ?
            (uint8_t)LAPSTATS_FLAG_CROSSING : (uint8_t)0;
    if (!cmdRssiNodePtr->getHistory().peakSend->isEmpty() &&
          (cmdRssiNodePtr->getHistory().nadirSend->isEmpty() ||
            (cmdRssiNodePtr->getHistory().peakSend->first().firstTime <
             cmdRssiNodePtr->getHistory().nadirSend->first().firstTime)))
    {
        flags |= LAPSTATS_FLAG_PEAK;
    }
    buffer.write8(flags);
    ioBufferWriteRssi(buffer, cmdRssiNodePtr->getLastPass().rssiNadir);  // lowest rssi since end of last pass
    ioBufferWriteRssi(buffer, cmdRssiNodePtr->getState().nodeRssiNadir);

    if (!cmdRssiNodePtr->getHistory().peakSend->isEmpty() &&
          (cmdRssiNodePtr->getHistory().nadirSend->isEmpty() ||
            (cmdRssiNodePtr->getHistory().peakSend->first().firstTime <
             cmdRssiNodePtr->getHistory().nadirSend->first().firstTime)))
    {
        // send peak
        ioBufferWriteExtremum(buffer, cmdRssiNodePtr->getHistory().peakSend->first(), timeNowVal);
        cmdRssiNodePtr->getHistory().peakSend->removeFirst();
    }
    else if (!cmdRssiNodePtr->getHistory().nadirSend->isEmpty() &&
              (cmdRssiNodePtr->getHistory().peakSend->isEmpty() ||
                (cmdRssiNodePtr->getHistory().nadirSend->first().firstTime <
                 cmdRssiNodePtr->getHistory().peakSend->first().firstTime)))
    {
        // send nadir
        ioBufferWriteExtremum(buffer, cmdRssiNodePtr->getHistory().nadirSend->first(), timeNowVal);
        cmdRssiNodePtr->getHistory().nadirSend->removeFirst();
    }
    else
    {
        ioBufferWriteRssi(buffer, 0);
        buffer.write16(0);
        buffer.write16(0);
    }
}
