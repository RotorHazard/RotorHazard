#ifndef commands_h
#define commands_h

#if TARGET != SIL_TARGET
#include <Stream.h>
#endif
#include "io.h"
#include "rssirx.h"
#include "hardware.h"

// API level for node; increment when commands are modified
constexpr uint16_t NODE_API_LEVEL = 33;

constexpr uint8_t MESSAGE_BUFFER_SIZE = 18;

class Message
{
private:
    void handleReadLapPassStats(RssiNode& rssiNode, mtime_t timeNowVal);
    void handleReadLapExtremums(RssiNode& rssiNode, mtime_t timeNowVal);
    void handleReadRssiHistory(RssiNode& rssiNode);
    void handleReadScanHistory(RssiNode& rssiNode);
    void setMode(RssiNode& rssiNode, Mode mode);
public:
    uint8_t command;  // code to identify messages
    Buffer<MESSAGE_BUFFER_SIZE> buffer;  // request/response payload

    uint8_t getPayloadSize();
    void handleWriteCommand(bool serialFlag);
    void handleReadCommand(bool serialFlag);
};

void handleStreamEvent(Stream& stream, Message& msg);

constexpr freq_t MIN_FREQ = 100;
constexpr freq_t MIN_SCAN_FREQ = 5645;
constexpr freq_t MAX_SCAN_FREQ = 5945;
constexpr freq_t MAX_FREQ = 9999;
constexpr uint16_t FREQ_INCR = 5;

#define READ_ADDRESS 0x00
#define READ_MODE 0x02
#define READ_FREQUENCY 0x03
#define READ_LAP_STATS 0x05
#define READ_LAP_PASS_STATS 0x0D
#define READ_LAP_EXTREMUMS 0x0E
#define READ_RHFEAT_FLAGS 0x11     // read feature flags value
#define READ_REVISION_CODE 0x22   // read NODE_API_LEVEL and verification value
#define READ_NODE_RSSI_PEAK 0x23  // read 'state.nodeRssiPeak' value
#define READ_NODE_RSSI_NADIR 0x24  // read 'state.nodeRssiNadir' value
#define READ_NODE_RSSI_HISTORY 0x25
#define READ_NODE_SCAN_HISTORY 0x26
#define READ_ENTER_AT_LEVEL 0x31
#define READ_EXIT_AT_LEVEL 0x32
#define READ_TIME_MILLIS 0x33     // read current 'millis()' value
#define READ_MULTINODE_COUNT 0x39  // read # of nodes handled by this processor
#define READ_CURNODE_INDEX 0x3A    // read index of current node for this processor
#define READ_NODE_SLOTIDX 0x3C     // read node slot index (for multi-node setup)

#define WRITE_FREQUENCY 0x51
#define WRITE_MODE 0x52
#define WRITE_ENTER_AT_LEVEL 0x71
#define WRITE_EXIT_AT_LEVEL 0x72
#define WRITE_CURNODE_INDEX 0x7A   // write index of current node for this processor

#define FORCE_END_CROSSING 0x78  // kill current crossing flag regardless of RSSI value
#define RESET_PAIRED_NODE 0x79  // command to reset node for ISP
#define JUMP_TO_BOOTLOADER 0x7E    // jump to bootloader for flash update

enum StatusFlag
{
    FREQ_SET        = 0x01,
    FREQ_CHANGED    = 0x02,
    ENTERAT_CHANGED = 0x04,
    EXITAT_CHANGED  = 0x08,
    COMM_ACTIVITY   = 0x10,
    POLLING         = 0x20,
    SERIAL_CMD_MSG  = 0x40
};

enum LapStatsFlag
{
    LAPSTATS_FLAG_CROSSING = 0x01, // crossing is in progress
    LAPSTATS_FLAG_PEAK     = 0x02  // reported extremum is peak
};

extern uint8_t cmdStatusFlags;
extern uint8_t cmdRssiNodeIndex;

// dummy macro
#define LOG_ERROR(...)

#endif
