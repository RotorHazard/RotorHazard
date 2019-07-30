#include "rhtypes.h"
#include "rssi.h"
#include "commands.h"

#ifdef __TEST__
  static uint8_t i2cSlaveAddress = 0x08;
#else
  extern uint8_t i2cSlaveAddress;
#endif

// API level for read/write commands; increment when commands are modified
#define NODE_API_LEVEL 18

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
void handleWriteCommand(Message_t *msg)
{
    uint16_t u16val;
    rssi_t rssiVal;

    msg->buffer.index = 0;

    switch (msg->command)
    {
        case WRITE_FREQUENCY:
            u16val = ioBufferRead16(&(msg->buffer));
            if (u16val >= MIN_FREQ && u16val <= MAX_FREQ) {
                if (u16val != settings.vtxFreq) {
                    settings.vtxFreq = u16val;
                    settingChangedFlags |= FREQ_CHANGED;
                }
                settingChangedFlags |= FREQ_SET;
            }
            break;

        case WRITE_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            rssiVal = ioBufferReadRssi(&(msg->buffer));
            if (rssiVal != settings.enterAtLevel) {
                settings.enterAtLevel = rssiVal;
                settingChangedFlags |= ENTERAT_CHANGED;
            }
            break;

        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            rssiVal = ioBufferReadRssi(&(msg->buffer));
            if (rssiVal != settings.exitAtLevel) {
                settings.exitAtLevel = rssiVal;
                settingChangedFlags |= EXITAT_CHANGED;
            }
            break;

        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
            rssiEndCrossing();
            break;

        default:
            LOG_ERROR("Invalid write command: ", msg->command, HEX);
    }

    msg->command = 0;  // Clear previous command
}

// Generic IO read command handler
void handleReadCommand(Message_t *msg)
{
    msg->buffer.size = 0;

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
              ioBufferWrite8(&(msg->buffer), state.crossing ? (uint8_t) 1 : (uint8_t) 0);  // 'crossing' status
              ioBufferWriteRssi(&(msg->buffer), lastPass.rssiNadir);  // lowest rssi since end of last pass
              ioBufferWriteRssi(&(msg->buffer), state.nodeRssiNadir);

              if (isPeakValid(history.peakSendRssi)) {
                  // send peak and reset
                  ioBufferWriteRssi(&(msg->buffer), history.peakSendRssi);
                  ioBufferWrite16(&(msg->buffer), uint16_t(now - history.peakSendFirstTime));
                  ioBufferWrite16(&(msg->buffer), uint16_t(now - history.peakSendLastTime));
                  history.peakSendRssi = 0;
              } else {
                  ioBufferWriteRssi(&(msg->buffer), 0);
                  ioBufferWrite16(&(msg->buffer), 0);
                  ioBufferWrite16(&(msg->buffer), 0);
              }

              if (isNadirValid(history.nadirSendRssi)) {
                  // send nadir and reset
                  ioBufferWriteRssi(&(msg->buffer), history.nadirSendRssi);
                  ioBufferWrite16(&(msg->buffer), uint16_t(now - history.nadirSendTime));
                  history.nadirSendRssi = MAX_RSSI;
              } else {
                  ioBufferWriteRssi(&(msg->buffer), 0);
                  ioBufferWrite16(&(msg->buffer), 0);
              }
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
    }

    if (msg->buffer.size > 0)
    {
        ioBufferWriteChecksum(&(msg->buffer));
    }

    msg->command = 0;  // Clear previous command
}
