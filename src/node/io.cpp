#include "io.h"

uint8_t ioBufferRead8(Buffer_t *buf)
{
    return buf->data[buf->index++];
}

uint16_t ioBufferRead16(Buffer_t *buf)
{
    uint16_t result;
    result = buf->data[buf->index++];
    result = (result << 8) | buf->data[buf->index++];
    return result;
}

uint32_t ioBufferRead32(Buffer_t *buf)
{
    uint32_t result;
    result = buf->data[buf->index++];
    result = (result << 8) | buf->data[buf->index++];
    result = (result << 8) | buf->data[buf->index++];
    result = (result << 8) | buf->data[buf->index++];
    return result;
}

void ioBufferWrite8(Buffer_t *buf, uint8_t data)
{
    buf->data[buf->size++] = data;
}

void ioBufferWrite16(Buffer_t *buf, uint16_t data)
{
    buf->data[buf->size++] = (data >> 8);
    buf->data[buf->size++] = data;
}

void ioBufferWrite32(Buffer_t *buf, uint32_t data)
{
    buf->data[buf->size++] = (data >> 24);
    buf->data[buf->size++] = (data >> 16);
    buf->data[buf->size++] = (data >> 8);
    buf->data[buf->size++] = data;
}

uint8_t ioCalculateChecksum(uint8_t *buf, byte size)
{
    uint8_t checksum = 0;
    for (int i = 0; i < size; i++)
    {
        checksum += buf[i];
    }
    return checksum;
}

void ioBufferWriteChecksum(Buffer_t *buf)
{
    uint8_t checksum = ioCalculateChecksum(buf->data, buf->size);
    ioBufferWrite8(buf, checksum);
}
