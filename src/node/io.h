#ifndef io_h
#define io_h

#include "config.h"

struct Buffer_s
{
    byte index = 0;
    byte size = 0;
    uint8_t data[20];  // Data array for I/O, up to 20 bytes per message
};

typedef struct Buffer_s Buffer_t;

uint8_t ioBufferRead8(Buffer_t *buf);
uint16_t ioBufferRead16(Buffer_t *buf);
uint32_t ioBufferRead32(Buffer_t *buf);

void ioBufferWrite8(Buffer_t *buf, uint8_t data);
void ioBufferWrite16(Buffer_t *buf, uint16_t data);
void ioBufferWrite32(Buffer_t *buf, uint32_t data);

uint8_t ioCalculateChecksum(uint8_t *buf, byte size);
void ioBufferWriteChecksum(Buffer_t *buf);

#define ioBufferReadRssi(buf) (ioBufferRead8(buf))
#define ioBufferWriteRssi(buf, rssi) (ioBufferWrite8(buf, rssi))

#endif
