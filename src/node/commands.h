#ifndef commands_h
#define commands_h

#include "io.h"
#include "rssirx.h"

// API level for node; increment when commands are modified
#define NODE_API_LEVEL 26

class Message
{
private:
    RssiReceivers *rssiRxs;
public:
    Message(RssiReceivers *rssiRxs) : rssiRxs(rssiRxs) {
    };
    uint8_t command;  // code to identify messages
    Buffer buffer;  // request/response payload

    byte getPayloadSize();
    void handleWriteCommand(bool serialFlag);
    void handleReadCommand(bool serialFlag);
};

#define MIN_FREQ 100
#define MAX_FREQ 9999

#define READ_ADDRESS 0x00
#define READ_FREQUENCY 0x03
#define READ_LAP_STATS 0x05
#define READ_REVISION_CODE 0x22   // read NODE_API_LEVEL and verification value
#define READ_NODE_RSSI_PEAK 0x23  // read 'state.nodeRssiPeak' value
#define READ_NODE_RSSI_NADIR 0x24  // read 'state.nodeRssiNadir' value
#define READ_ENTER_AT_LEVEL 0x31
#define READ_EXIT_AT_LEVEL 0x32
#define READ_TIME_MILLIS 0x33     // read current 'millis()' value
#define READ_MULTINODE_COUNT 0x39  // read # of nodes handled by this processor
#define READ_CURNODE_INDEX 0x3A    // read index of current node for this processor

#define WRITE_FREQUENCY 0x51
#define WRITE_ENTER_AT_LEVEL 0x71
#define WRITE_EXIT_AT_LEVEL 0x72
#define WRITE_CURNODE_INDEX 0x7A   // write index of current node for this processor

#define FORCE_END_CROSSING 0x78  // kill current crossing flag regardless of RSSI value
#define RESET_PAIRED_NODE 0x79  // command to reset node for ISP

#define FREQ_SET        0x01
#define FREQ_CHANGED    0x02
#define ENTERAT_CHANGED 0x04
#define EXITAT_CHANGED  0x08
#define COMM_ACTIVITY   0x10
#define LAPSTATS_READ   0x20
#define SERIAL_CMD_MSG  0x40

#define LAPSTATS_FLAG_CROSSING 0x01  // crossing is in progress
#define LAPSTATS_FLAG_PEAK 0x02      // reported extremum is peak

extern uint8_t settingChangedFlags;
extern uint8_t cmdRssiNodeIndex;

// dummy macro
#define LOG_ERROR(...)

#endif
