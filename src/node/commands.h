#ifndef commands_h
#define commands_h

#if TARGET != SIL_TARGET
#include <Stream.h>
#endif
#include "io.h"
#include "rssirx.h"
#include "hardware.h"

// API level for node; increment when commands are modified
#define NODE_API_LEVEL 33

#define MESSAGE_BUFFER_SIZE 18

class Message
{
private:
    void handleReadLapPassStats(RssiNode& rssiNode, mtime_t timeNowVal);
    void handleReadLapExtremums(RssiNode& rssiNode, mtime_t timeNowVal);
    void handleReadRssiHistory(RssiNode& rssiNode);
    void setMode(RssiNode& rssiNode, uint8_t mode);
public:
    uint8_t command;  // code to identify messages
    Buffer<MESSAGE_BUFFER_SIZE> buffer;  // request/response payload

    uint8_t getPayloadSize();
    void handleWriteCommand(bool serialFlag);
    void handleReadCommand(bool serialFlag);
};

void handleStreamEvent(Stream& stream, Message& msg);

#define MIN_FREQ 100
#define MAX_FREQ 9999

#define READ_ADDRESS 0x00
#define READ_FREQUENCY 0x03
#define READ_LAP_STATS 0x05
#define READ_LAP_PASS_STATS 0x0D
#define READ_LAP_EXTREMUMS 0x0E
#define READ_RHFEAT_FLAGS 0x11     // read feature flags value
#define READ_REVISION_CODE 0x22   // read NODE_API_LEVEL and verification value
#define READ_NODE_RSSI_PEAK 0x23  // read 'state.nodeRssiPeak' value
#define READ_NODE_RSSI_NADIR 0x24  // read 'state.nodeRssiNadir' value
#define READ_NODE_RSSI_HISTORY 0x25
#define READ_ENTER_AT_LEVEL 0x31
#define READ_EXIT_AT_LEVEL 0x32
#define READ_TIME_MILLIS 0x33     // read current 'millis()' value
#define READ_MULTINODE_COUNT 0x39  // read # of nodes handled by this processor
#define READ_CURNODE_INDEX 0x3A    // read index of current node for this processor
#define READ_NODE_SLOTIDX 0x3C     // read node slot index (for multi-node setup)

#define WRITE_FREQUENCY 0x51
#define WRITE_ENTER_AT_LEVEL 0x71
#define WRITE_EXIT_AT_LEVEL 0x72
#define WRITE_MODE 0x73
#define WRITE_CURNODE_INDEX 0x7A   // write index of current node for this processor

#define FORCE_END_CROSSING 0x78  // kill current crossing flag regardless of RSSI value
#define RESET_PAIRED_NODE 0x79  // command to reset node for ISP
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

#define MODE_TIMER 0
#define MODE_SCANNER 1
#define MODE_RAW 2

extern uint8_t cmdStatusFlags;
extern uint8_t cmdRssiNodeIndex;

// dummy macro
#define LOG_ERROR(...)

#endif
