#include "rhtypes.h"
#include "rssi.h"
#include "commands.h"
#include "resetNode.h"

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

        default:  // invalid command
            LOG_ERROR("Invalid write command: ", command, HEX);
            size = -1;
    }
    return size;
}

// Generic IO write command handler
void handleWriteCommand(Message_t *msg, bool serialFlag)
{
    uint8_t u8val;
    uint16_t u16val;
    rssi_t rssiVal;

    msg->buffer.index = 0;
    bool actFlag = true;

    switch (msg->command)
    {
        case WRITE_FREQUENCY:
            u16val = ioBufferRead16(&(msg->buffer));
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
            rssiVal = ioBufferReadRssi(&(msg->buffer));
            if (rssiVal != settings.enterAtLevel)
            {
                settings.enterAtLevel = rssiVal;
                settingChangedFlags |= ENTERAT_CHANGED;
            }
            break;

        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            rssiVal = ioBufferReadRssi(&(msg->buffer));
            if (rssiVal != settings.exitAtLevel)
            {
                settings.exitAtLevel = rssiVal;
                settingChangedFlags |= EXITAT_CHANGED;
            }
            break;

        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
            rssiEndCrossing();
            break;

        case CLOSE_SERIAL:  // end Serial so ISP can be performed
            endSerial();
            break;

        case RESET_PAIRED_NODE:  // reset paired node for ISP
            u8val = ioBufferRead8(&(msg->buffer));
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

void ioBufferWriteExtremum(Buffer_t *buf, Extremum *e, mtime_t now)
{
    ioBufferWriteRssi(buf, e->rssi);
    ioBufferWrite16(buf, uint16_t(now - e->firstTime));
    ioBufferWrite16(buf, uint16_t(now - e->firstTime - e->duration));
}

// Generic IO read command handler
void handleReadCommand(Message_t *msg, bool serialFlag)
{
    msg->buffer.size = 0;
    bool actFlag = true;

    switch (msg->command)
    {
        case READ_ADDRESS:
            ioBufferWrite8(&(msg->buffer), i2cSlaveAddress);
            break;

        case READ_FREQUENCY:
            ioBufferWrite16(&(msg->buffer), settings.vtxFreq);
            break;

        case READ_LAP_STATS:
            {
            mtime_t now = millis();
            ioBufferWrite8(&(msg->buffer), lastPass.lap);
            ioBufferWrite16(&(msg->buffer), uint16_t(now - lastPass.timestamp));  // ms since lap
            ioBufferWriteRssi(&(msg->buffer), state.rssi);
            ioBufferWriteRssi(&(msg->buffer), state.nodeRssiPeak);
            ioBufferWriteRssi(&(msg->buffer), lastPass.rssiPeak);  // RSSI peak for last lap pass
            ioBufferWrite16(&(msg->buffer), uint16_t(state.loopTimeMicros));
            // set flag if 'crossing' in progress
            uint8_t flags = state.crossing ? (uint8_t)LAPSTATS_FLAG_CROSSING : (uint8_t)0;
            if (isPeakValid(history.peakSend) && (!isNadirValid(history.nadirSend)
                    || (history.peakSend.firstTime < history.nadirSend.firstTime)))
            {
                flags |= LAPSTATS_FLAG_PEAK;
            }
            ioBufferWrite8(&(msg->buffer), flags);
            ioBufferWriteRssi(&(msg->buffer), lastPass.rssiNadir);  // lowest rssi since end of last pass
            ioBufferWriteRssi(&(msg->buffer), state.nodeRssiNadir);

            if ((flags & (uint8_t)LAPSTATS_FLAG_PEAK) != (uint8_t)0)
            {
                // send peak and reset
                ioBufferWriteExtremum(&(msg->buffer), &(history.peakSend), now);
                history.peakSend.rssi = 0;
            }
            else if (isNadirValid(history.nadirSend)
                  && (!isPeakValid(history.peakSend)
                    || (history.nadirSend.firstTime < history.peakSend.firstTime)))
            {
                // send nadir and reset
                ioBufferWriteExtremum(&(msg->buffer), &(history.nadirSend), now);
                history.nadirSend.rssi = MAX_RSSI;
            }
            else
            {
                ioBufferWriteRssi(&(msg->buffer), 0);
                ioBufferWrite16(&(msg->buffer), 0);
                ioBufferWrite16(&(msg->buffer), 0);
            }

            settingChangedFlags |= LAPSTATS_READ;

            }
            break;

        case READ_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            ioBufferWriteRssi(&(msg->buffer), settings.enterAtLevel);
            break;

        case READ_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            ioBufferWriteRssi(&(msg->buffer), settings.exitAtLevel);
            break;

        case READ_REVISION_CODE:  // reply with NODE_API_LEVEL and verification value
            ioBufferWrite16(&(msg->buffer), (0x25 << 8) + NODE_API_LEVEL);
            break;

        case READ_NODE_RSSI_PEAK:
            ioBufferWriteRssi(&(msg->buffer), state.nodeRssiPeak);
            break;

        case READ_NODE_RSSI_NADIR:
            ioBufferWriteRssi(&(msg->buffer), state.nodeRssiNadir);
            break;

        case READ_TIME_MILLIS:
            ioBufferWrite32(&(msg->buffer), millis());
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

    if (msg->buffer.size > 0)
    {
        ioBufferWriteChecksum(&(msg->buffer));
    }

    msg->command = 0;  // Clear previous command
}
