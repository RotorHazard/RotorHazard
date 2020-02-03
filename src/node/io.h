#ifndef io_h
#define io_h

#include "config.h"

class Buffer {
    public:
        uint8_t index = 0;
        uint8_t size = 0;
        uint8_t data[20];  // Data array for I/O, up to 20 bytes per message

        bool isEmpty() {
            return size == 0;
        }
        void flipForRead() {
            index = 0;
        }
        void flipForWrite() {
            size = 0;
        }
        uint8_t read8() {
            return data[index++];
        }
        uint16_t read16() {
            uint16_t result;
            result = data[index++];
            result = (result << 8) | data[index++];
            return result;
        }
        uint32_t read32() {
            uint32_t result;
            result = data[index++];
            result = (result << 8) | data[index++];
            result = (result << 8) | data[index++];
            result = (result << 8) | data[index++];
            return result;
        }
        void write8(uint8_t v) {
            data[size++] = v;
        }
        void write16(uint16_t v) {
            data[size++] = (v >> 8);
            data[size++] = v;
        }
        void write32(uint32_t v) {
            data[size++] = (v >> 24);
            data[size++] = (v >> 16);
            data[size++] = (v >> 8);
            data[size++] = v;
        }
        uint8_t calculateChecksum(uint8_t len) {
            uint8_t checksum = 0;
            for (int i = 0; i < len; i++)
            {
                checksum += data[i];
            }
            return checksum;
        }
        void writeChecksum() {
            uint8_t checksum = calculateChecksum(size);
            write8(checksum);
        }
};

#define ioBufferReadRssi(buf) (buf.read8())
#define ioBufferWriteRssi(buf, rssi) (buf.write8(rssi))

#endif
