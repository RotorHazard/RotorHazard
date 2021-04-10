#ifndef commands_h
#define commands_h

#include "io.h"

// API level for node; increment when commands are modified
#define NODE_API_LEVEL 35

class Message
{
public:
    uint8_t command;  // code to identify messages
    Buffer buffer;  // request/response payload

    byte getPayloadSize();
    void handleWriteCommand(bool serialFlag);
    void handleReadCommand(bool serialFlag);
    void handleReadLapPassStats(mtime_t timeNowVal);
    void handleReadLapExtremums(mtime_t timeNowVal);
};

#define MIN_FREQ 100
#define MAX_FREQ 9999

#define READ_ADDRESS 0x00
#define READ_FREQUENCY 0x03
#define READ_LAP_STATS 0x05
#define READ_LAP_PASS_STATS 0x0D
#define READ_LAP_EXTREMUMS 0x0E
#define READ_RHFEAT_FLAGS 0x11     // read feature flags value
#define READ_REVISION_CODE 0x22    // read NODE_API_LEVEL and verification value
#define READ_NODE_RSSI_PEAK 0x23   // read 'state.nodeRssiPeak' value
#define READ_NODE_RSSI_NADIR 0x24  // read 'state.nodeRssiNadir' value
#define READ_ENTER_AT_LEVEL 0x31
#define READ_EXIT_AT_LEVEL 0x32
#define READ_TIME_MILLIS 0x33      // read current 'millis()' value
#define READ_MULTINODE_COUNT 0x39  // read # of nodes handled by this processor
#define READ_CURNODE_INDEX 0x3A    // read index of current node for this processor
#define READ_NODE_SLOTIDX 0x3C     // read node slot index (for multi-node setup)
#define READ_FW_VERSION 0x3D       // read firmware version string
#define READ_FW_BUILDDATE 0x3E     // read firmware build date string
#define READ_FW_BUILDTIME 0x3F     // read firmware build time string
#define READ_FW_PROCTYPE 0x40      // read node processor type

#define WRITE_FREQUENCY 0x51
#define WRITE_ENTER_AT_LEVEL 0x71
#define WRITE_EXIT_AT_LEVEL 0x72
#define WRITE_CURNODE_INDEX 0x7A   // write index of current node for this processor

#define SEND_STATUS_MESSAGE 0x75   // send status message from server to node
#define FORCE_END_CROSSING 0x78    // kill current crossing flag regardless of RSSI value
#define RESET_PAIRED_NODE 0x79     // command to reset node for ISP
#define JUMP_TO_BOOTLOADER 0x7E    // jump to bootloader for flash update

#define FREQ_SET        0x01
#define FREQ_CHANGED    0x02
#define ENTERAT_CHANGED 0x04
#define EXITAT_CHANGED  0x08
#define COMM_ACTIVITY   0x10
#define LAPSTATS_READ   0x20
#define SERIAL_CMD_MSG  0x40

#define LAPSTATS_FLAG_CROSSING 0x01  // crossing is in progress
#define LAPSTATS_FLAG_PEAK 0x02      // reported extremum is peak

// upper-byte values for SEND_STATUS_MESSAGE payload (lower byte is data)
#define STATMSG_SDBUTTON_STATE 0x01    // shutdown button state (1=pressed, 0=released)
#define STATMSG_SHUTDOWN_STARTED 0x02  // system shutdown started
#define STATMSG_SERVER_IDLE 0x03       // server-idle tick message

RssiNode *getCmdRssiNodePtr();

extern uint8_t settingChangedFlags;

// dummy macro
#define LOG_ERROR(...)

#endif
