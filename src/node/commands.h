#ifndef commands_h
#define commands_h

#if TARGET != SIL_TARGET
#include <Stream.h>
#endif
#include "io.h"
#include "rssirx.h"
#include "hardware.h"

// API level for node; increment when commands are modified
constexpr uint16_t NODE_API_LEVEL = 35;

constexpr freq_t MIN_FREQ = 100;
constexpr freq_t MAX_FREQ = 9999;

enum CommSource
{
    I2C_SOURCE = 1,
    SERIAL_SOURCE = 2,
    WIFI_SOURCE = 3
};

enum Command: uint8_t
{
    READ_ADDRESS = 0x00,
    READ_MODE = 0x02,
    READ_FREQUENCY = 0x03,
    READ_LAP_STATS = 0x05,
    READ_LAP_PASS_STATS = 0x0D,
    READ_LAP_EXTREMUMS = 0x0E,
    READ_RHFEAT_FLAGS = 0x11,    // read feature flags value
    READ_REVISION_CODE = 0x22,   // read NODE_API_LEVEL and verification value
    READ_NODE_RSSI_PEAK = 0x23,  // read 'state.nodeRssiPeak' value
    READ_NODE_RSSI_NADIR = 0x24, // read 'state.nodeRssiNadir' value
    READ_NODE_RSSI_HISTORY = 0x25,
    READ_NODE_SCAN_HISTORY = 0x26,
    READ_ENTER_AT_LEVEL = 0x31,
    READ_EXIT_AT_LEVEL = 0x32,
    READ_TIME_MILLIS = 0x33,     // read current 'millis()' value
    READ_MULTINODE_COUNT = 0x39, // read # of nodes handled by this processor
    READ_CURNODE_INDEX = 0x3A,   // read index of current node for this processor
    READ_NODE_SLOTIDX = 0x3C,    // read node slot index (for multi-node setup)
    READ_FW_VERSION = 0x3D,      // read firmware version string
    READ_FW_BUILDDATE = 0x3E,    // read firmware build date string
    READ_FW_BUILDTIME = 0x3F,    // read firmware build time string
    READ_FW_PROCTYPE = 0x40,     // read node processor type

    WRITE_FREQUENCY = 0x51,
    WRITE_MODE = 0x52,
    WRITE_ENTER_AT_LEVEL = 0x71,
    WRITE_EXIT_AT_LEVEL = 0x72,
    WRITE_CURNODE_INDEX = 0x7A,  // write index of current node for this processor

    SEND_STATUS_MESSAGE = 0x75,  // send status message from server to node
    FORCE_END_CROSSING = 0x78,   // kill current crossing flag regardless of RSSI value
    RESET_PAIRED_NODE = 0x79,    // command to reset node for ISP
    JUMP_TO_BOOTLOADER = 0x7E,   // jump to bootloader for flash update
    INVALID_COMMAND = 0xFF
};

// maximum possible message size is limited to 32 bytes by I2C
constexpr uint8_t MESSAGE_BUFFER_SIZE = 18;
// maximum possible text size is MESSAGE_BUFFER_SIZE-2 (command byte + checksum byte)
// text is inclusive of a null-terminator
constexpr uint8_t TEXT_SIZE = 16;

constexpr bool isWriteCommand(uint8_t cmd) { return cmd > 0x50; };

class Message
{
private:
    void handleReadLapPassStats(RssiNode& rssiNode, mtime_t timeNowVal);
    void handleReadLapExtremums(RssiNode& rssiNode, mtime_t timeNowVal);
    void handleReadRssiHistory(RssiNode& rssiNode);
    void handleReadScanHistory(RssiNode& rssiNode);
    void setMode(RssiNode& rssiNode, Mode mode) const;
public:
    Command command = INVALID_COMMAND;  // code to identify messages
    Buffer<MESSAGE_BUFFER_SIZE,TEXT_SIZE> buffer;  // request/response payload

    inline bool isWriteCommand() const { return ::isWriteCommand(command); };
    int_fast8_t getPayloadSize() const;
    void handleWriteCommand(CommSource src);
    void handleReadCommand(CommSource src);
};

void handleStreamEvent(Stream& stream, Message& msg, CommSource src);
void sendReadCommandResponse(Stream& stream, Message& msg);
void validateAndProcessWriteCommand(Message& msg, CommSource src);

enum StatusFlag: uint8_t
{
    NO_STATUS       = 0x0,
    COMM_ACTIVITY   = 0x1,
    POLLING         = 0x2,
    SERIAL_CMD_MSG  = 0x4
};

enum LapStatsFlag: uint8_t
{
    LAPSTATS_FLAG_CROSSING = 0x01, // crossing is in progress
    LAPSTATS_FLAG_PEAK     = 0x02  // reported extremum is peak
};

extern uint8_t volatile cmdStatusFlags;
extern uint_fast8_t volatile cmdRssiNodeIndex;

// dummy macro
#define LOG_ERROR(...)

#endif
