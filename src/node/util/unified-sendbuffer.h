#ifndef unifiedsendbuffer_h
#define unifiedsendbuffer_h

#include "rhtypes.h"
#include "sendbuffer.h"
#include "CircularBuffer.h"

template <typename T, uint8_t N> class UnifiedSendBuffer : public SendBuffer<T>, public List<T,N>
{
    private:
        ExtremumType lastAddedType = NONE;
        CircularBuffer<T,N> buffer;
    public:
        T operator [] (uint8_t index) const {
            return buffer[index];
        }
        uint8_t inline size() const {
            return buffer.size();
        }
        bool addPeak(const T& peak, bool force = false) {
            if (lastAddedType != PEAK) {
                buffer.push(peak);
                lastAddedType = PEAK;
                return true;
            } else {
                return false;
            }
        }
        bool addNadir(const T& nadir, bool force = false) {
            if (lastAddedType != NADIR) {
                buffer.push(nadir);
                lastAddedType = NADIR;
                return true;
            } else {
                return false;
            }
        }
        const T nextPeak() {
            if (nextType() == NADIR && buffer.size() > 1) {
                return buffer[1];
            } else {
                return buffer.first();
            }
        }
        const T nextNadir() {
            if (nextType() == PEAK && buffer.size() > 1) {
                return buffer[1];
            } else {
                return buffer.first();
            }
        }
        ExtremumType nextType() {
            if (buffer.isEmpty()) {
                return NONE;
            } else if (lastAddedType == PEAK) {
                return buffer.size()&1 ? PEAK : NADIR;
            } else if (lastAddedType == NADIR) {
                return buffer.size()&1 ? NADIR : PEAK;
            } else {
                return NONE;
            }
        }
        const T popNext() {
            return buffer.shift();
        }
        void clear() {
            buffer.clear();
            lastAddedType = NONE;
        }
};

#endif
