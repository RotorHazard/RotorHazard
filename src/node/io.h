#ifndef io_h
#define io_h

#include "config.h"

#define TEXT_BLOCK_SIZE 16   // length oc:\Users\RaceF\OneDrive\Documents\Arduino\node_id_button\config.h c:\Users\RaceF\OneDrive\Documents\Arduino\node_id_button\commands.cpp c:\Users\RaceF\OneDrive\Documents\Arduino\node_id_button\commands.hf data for 'writeTextBlock()'

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
        void writeTextBlock(const char *srcStr) {
            const char *sPtr = srcStr;
            int p = 0;
            while (*sPtr > ' ' && ++p < 99)  // find first space
                ++sPtr;
            if (p < 99) {
                p = 0;
                do {  // copy data until null (or length limit)
                    ++sPtr;
                    write8(*sPtr);
                }
                while(++p < TEXT_BLOCK_SIZE && *sPtr > '\0');
            }
            else
                p = 0;
            while(p < TEXT_BLOCK_SIZE) {  // pad rest with nulls
                write8('\0');
                ++p;
            }
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
