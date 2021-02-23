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
        uint8_t nextToSendIndex = 0;

        void add(const T& e) {
            if (!buffer.push(e)) {
                if (nextToSendIndex > 0) {
                    nextToSendIndex--;
                }
            }
        }
#ifdef __TEST__
public:
#endif
        uint8_t remainingToSend() const {
            return buffer.size() - nextToSendIndex;
        }
    public:
        T operator [] (uint8_t index) const {
            return buffer[index];
        }
        const ExtremumType typeAt(uint8_t index) const {
            if (index >= buffer.size()) {
                return NONE;
            } else {
                uint8_t rem = buffer.size() - index;
                if (lastAddedType == PEAK) {
                    return rem&1 ? PEAK : NADIR;
                } else if (lastAddedType == NADIR) {
                    return rem&1 ? NADIR : PEAK;
                } else {
                    return NONE;
                }
            }
        }
        uint8_t size() const {
            return buffer.size();
        }
        bool addPeak(const T& peak, bool force = false) {
            if (lastAddedType != PEAK) {
                add(peak);
                lastAddedType = PEAK;
                return true;
            } else {
                return false;
            }
        }
        bool addNadir(const T& nadir, bool force = false) {
            if (lastAddedType != NADIR) {
                add(nadir);
                lastAddedType = NADIR;
                return true;
            } else {
                return false;
            }
        }
        const T nextPeak() {
            if (nextType() == NADIR && remainingToSend() > 1) {
                return buffer[nextToSendIndex+1];
            } else {
                return buffer[nextToSendIndex];
            }
        }
        const T nextNadir() {
            if (nextType() == PEAK && remainingToSend() > 1) {
                return buffer[nextToSendIndex+1];
            } else {
                return buffer[nextToSendIndex];
            }
        }
        const ExtremumType nextType() {
            return remainingToSend() > 0 ? typeAt(nextToSendIndex) : NONE;
        }
        const T popNext() {
            T next = buffer[nextToSendIndex];
            if (nextToSendIndex < buffer.size()) {
                nextToSendIndex++;
            }
            return next;
        }
        void removeLast() {
            buffer.pop();
            if (buffer.size() == 0) {
                lastAddedType = NONE;
            } else if (lastAddedType == PEAK) {
                lastAddedType = NADIR;
            } else if (lastAddedType == NADIR) {
                lastAddedType = PEAK;
            } else {
                lastAddedType = NONE;
            }
        }
        void clear() {
            buffer.clear();
            lastAddedType = NONE;
            nextToSendIndex = 0;
        }
};

#endif
