#ifndef commands_h
#define commands_h

#include "io.h"

// API level for read/write commands; increment when commands are modified
#define NODE_API_LEVEL 19

struct Message_s
{
    uint8_t command;  // code to identify messages
    Buffer_t buffer;  // request/response payload
};

typedef struct Message_s Message_t;

#define MIN_FREQ 5645
#define MAX_FREQ 5945

#define READ_ADDRESS 0x00
#define READ_FREQUENCY 0x03
#define READ_LAP_STATS 0x05
#define READ_FILTER_RATIO 0x20    // API_level>=10 uses 16-bit value
#define READ_REVISION_CODE 0x22   // read NODE_API_LEVEL and verification value
#define READ_NODE_RSSI_PEAK 0x23  // read 'state.nodeRssiPeak' value
#define READ_NODE_RSSI_NADIR 0x24  // read 'state.nodeRssiNadir' value
#define READ_ENTER_AT_LEVEL 0x31
#define READ_EXIT_AT_LEVEL 0x32
#define READ_TIME_MILLIS 0x33     // read current 'millis()' value

#define WRITE_FREQUENCY 0x51
#define WRITE_FILTER_RATIO 0x70   // API_level>=10 uses 16-bit value
#define WRITE_ENTER_AT_LEVEL 0x71
#define WRITE_EXIT_AT_LEVEL 0x72

#define FORCE_END_CROSSING 0x78  // kill current crossing flag regardless of RSSI value

#define FREQ_SET        0x01
#define FREQ_CHANGED    0x02
#define ENTERAT_CHANGED 0x04
#define EXITAT_CHANGED  0x08

byte getPayloadSize(uint8_t command);
void handleWriteCommand(Message_t *msg);
void handleReadCommand(Message_t *msg);

extern uint8_t settingChangedFlags;

// dummy macro
#define LOG_ERROR(...)

#endif
