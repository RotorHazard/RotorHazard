#ifndef io_h
#define io_h

#include "config.h"

template<size_t S> class Buffer {
    public:
        uint8_t index = 0;
        uint8_t size = 0;
        uint8_t data[S];  // Data array for I/O, up to 18 bytes per message

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
            if (index < S) {
                return data[index++];
            } else {
                return 0xFF;
            }
        }
        uint16_t read16() {
            if (index < S-1) {
                uint16_t result;
                result = data[index++];
                result = (result << 8) | data[index++];
                return result;
            } else {
                return 0xFFFF;
            }
        }
        uint32_t read32() {
            if (index < S-3) {
                uint32_t result;
                result = data[index++];
                result = (result << 8) | data[index++];
                result = (result << 8) | data[index++];
                result = (result << 8) | data[index++];
                return result;
            } else {
                return 0xFFFFFFFF;
            }
        }
        void write8(uint8_t v) {
            if (size < S) {
                data[size++] = v;
            }
        }
        void write16(uint16_t v) {
            if (size < S-1) {
                data[size++] = (v >> 8);
                data[size++] = v;
            }
        }
        void write32(uint32_t v) {
            if (size < S-3) {
                data[size++] = (v >> 24);
                data[size++] = (v >> 16);
                data[size++] = (v >> 8);
                data[size++] = v;
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

template<size_t N> constexpr rssi_t ioBufferReadRssi(Buffer<N>& buf) { return buf.read8(); }
template<size_t N> constexpr void ioBufferWriteRssi(Buffer<N>& buf, rssi_t rssi) { buf.write8(rssi); }
template<size_t N> constexpr void ioBufferWriteFreqRssi(Buffer<N>& buf, const FreqRssi& f_r) { buf.write16(f_r.freq); buf.write8(f_r.rssi); }

#endif
