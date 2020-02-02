#include "config.h"
#include "rhtypes.h"
#include "rssi.h"
#include "commands.h"

#ifdef __TEST__
  static uint8_t i2cSlaveAddress = 0x08;
#else
  extern uint8_t i2cSlaveAddress;
#endif

uint8_t settingChangedFlags = 0;

byte getPayloadSize(uint8_t command)
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
void handleWriteCommand(Message_t *msg, bool serialFlag)
{
    uint8_t u8val;
    uint16_t u16val;
    rssi_t rssiVal;

    msg->buffer.flipForRead();
    bool actFlag = true;

    switch (msg->command)
    {
        case WRITE_FREQUENCY:
            u16val = msg->buffer.read16();
            if (u16val >= MIN_FREQ && u16val <= MAX_FREQ)
            {
                if (u16val != settings.vtxFreq)
                {
                    settings.vtxFreq = u16val;
                    settingChangedFlags |= FREQ_CHANGED;
                }
                settingChangedFlags |= FREQ_SET;
            }
            break;

        case WRITE_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            rssiVal = ioBufferReadRssi(msg->buffer);
            if (rssiVal != settings.enterAtLevel)
            {
                settings.enterAtLevel = rssiVal;
                settingChangedFlags |= ENTERAT_CHANGED;
            }
            break;

        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            rssiVal = ioBufferReadRssi(msg->buffer);
            if (rssiVal != settings.exitAtLevel)
            {
                settings.exitAtLevel = rssiVal;
                settingChangedFlags |= EXITAT_CHANGED;
            }
            break;

        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
            rssiEndCrossing();
            break;

        case RESET_PAIRED_NODE:  // reset paired node for ISP
            u8val = msg->buffer.read8();
            resetPairedNode(u8val);
            break;

        default:
            LOG_ERROR("Invalid write command: ", msg->command, HEX);
            actFlag = false;  // not valid activity
    }

    // indicate communications activity detected
    if (actFlag)
    {
        settingChangedFlags |= COMM_ACTIVITY;
        if (serialFlag)
            settingChangedFlags |= SERIAL_CMD_MSG;
    }

    msg->command = 0;  // Clear previous command
}

void ioBufferWriteExtremum(Buffer& buf, const Extremum& e, mtime_t now)
{
    ioBufferWriteRssi(buf, e.rssi);
    buf.write16(uint16_t(now - e.firstTime));
    buf.write16(uint16_t(now - e.firstTime - e.duration));
}

// Generic IO read command handler
void handleReadCommand(Message_t *msg, bool serialFlag)
{
    msg->buffer.flipForWrite();
    bool actFlag = true;

    switch (msg->command)
    {
        case READ_ADDRESS:
            msg->buffer.write8(i2cSlaveAddress);
            break;

        case READ_FREQUENCY:
            msg->buffer.write16(settings.vtxFreq);
            break;

        case READ_LAP_STATS:
            {
            mtime_t now = millis();
            msg->buffer.write8(lastPass.lap);
            msg->buffer.write16(uint16_t(now - lastPass.timestamp));  // ms since lap
            ioBufferWriteRssi(msg->buffer, state.rssi);
            ioBufferWriteRssi(msg->buffer, state.nodeRssiPeak);
            ioBufferWriteRssi(msg->buffer, lastPass.rssiPeak);  // RSSI peak for last lap pass
            msg->buffer.write16(uint16_t(state.loopTimeMicros));
            // set flag if 'crossing' in progress
            uint8_t flags = state.crossing ? (uint8_t)LAPSTATS_FLAG_CROSSING : (uint8_t)0;
            if (!history.peakSend.isEmpty()
                  && (history.nadirSend.isEmpty()
                    || (history.peakSend.first().firstTime < history.nadirSend.first().firstTime)))
            {
                flags |= LAPSTATS_FLAG_PEAK;
            }
            msg->buffer.write8(flags);
            ioBufferWriteRssi(msg->buffer, lastPass.rssiNadir);  // lowest rssi since end of last pass
            ioBufferWriteRssi(msg->buffer, state.nodeRssiNadir);

            if (!history.peakSend.isEmpty()
                  && (history.nadirSend.isEmpty()
                    || (history.peakSend.first().firstTime < history.nadirSend.first().firstTime)))
            {
                // send peak
                ioBufferWriteExtremum(msg->buffer, history.peakSend.first(), now);
                history.peakSend.removeFirst();
            }
            else if (!history.nadirSend.isEmpty()
                  && (history.peakSend.isEmpty()
                    || (history.nadirSend.first().firstTime < history.peakSend.first().firstTime)))
            {
                // send nadir
                ioBufferWriteExtremum(msg->buffer, history.nadirSend.first(), now);
                history.nadirSend.removeFirst();
            }
            else
            {
                ioBufferWriteRssi(msg->buffer, 0);
                msg->buffer.write16(0);
                msg->buffer.write16(0);
            }

            settingChangedFlags |= LAPSTATS_READ;

            }
            break;

        case READ_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            ioBufferWriteRssi(msg->buffer, settings.enterAtLevel);
            break;

        case READ_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            ioBufferWriteRssi(msg->buffer, settings.exitAtLevel);
            break;

        case READ_REVISION_CODE:  // reply with NODE_API_LEVEL and verification value
            msg->buffer.write16((0x25 << 8) + NODE_API_LEVEL);
            break;

        case READ_NODE_RSSI_PEAK:
            ioBufferWriteRssi(msg->buffer, state.nodeRssiPeak);
            break;

        case READ_NODE_RSSI_NADIR:
            ioBufferWriteRssi(msg->buffer, state.nodeRssiNadir);
            break;

        case READ_TIME_MILLIS:
            msg->buffer.write32(millis());
            break;

        default:  // If an invalid command is sent, write nothing back, master must react
            LOG_ERROR("Invalid read command: ", msg->command, HEX);
            actFlag = false;  // not valid activity
    }

    // indicate communications activity detected
    if (actFlag)
    {
        settingChangedFlags |= COMM_ACTIVITY;
        if (serialFlag)
            settingChangedFlags |= SERIAL_CMD_MSG;
    }

    if (!msg->buffer.isEmpty())
    {
        msg->buffer.writeChecksum();
    }

    msg->command = 0;  // Clear previous command
}
