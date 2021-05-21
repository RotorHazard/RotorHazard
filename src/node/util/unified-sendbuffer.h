#ifndef unifiedsendbuffer_h
#define unifiedsendbuffer_h

#include "rhtypes.h"
#include "sendbuffer.h"
#include "CircularBuffer.h"

template <typename T, uint8_t N> class UnifiedSendBuffer : public SendBuffer<T>, public List<T,N>
{
    private:
        ExtremumType lastAddedType = NONE;
        uint_fast8_t nextToSendIndex = 0;

    protected:
        CircularBuffer<T,N> buffer;

        virtual bool add(const T& e) {
            bool hadCapacity = buffer.push(e);
            if (!hadCapacity) {
                if (nextToSendIndex > 0) {
                    nextToSendIndex--;
                }
            }
            return hadCapacity;
        }

#ifdef __TEST__
public:
#endif
        uint_fast8_t remainingToSend() const {
            return buffer.size() - nextToSendIndex;
        }
    public:
        T operator [] (uint_fast8_t index) const {
            return buffer[index];
        }
        const ExtremumType typeAt(uint_fast8_t index) const {
            if (index >= buffer.size()) {
                return NONE;
            } else {
                uint_fast8_t rem = buffer.size() - index;
                if (lastAddedType == PEAK) {
                    return rem&1 ? PEAK : NADIR;
                } else if (lastAddedType == NADIR) {
                    return rem&1 ? NADIR : PEAK;
                } else {
                    return NONE;
                }
            }
        }
        uint_fast8_t size() const {
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

template <uint8_t N> class SortedUnifiedSendBuffer : public UnifiedSendBuffer<Extremum,N> {
    public:
        uint_fast8_t sortedIdxs[N];

    protected:
        bool add(const Extremum& e) {
            bool hadCapacity = UnifiedSendBuffer<Extremum,N>::add(e);
            if (!hadCapacity) {
                const int_fast8_t lastIdx = UnifiedSendBuffer<Extremum,N>::buffer.size()-1;
                int_fast8_t shift = 0;
                for (int_fast8_t i=0; i<lastIdx; i++) {
                    if (sortedIdxs[i] == 0) {
                        shift = 1;
                    }
                    sortedIdxs[i] = sortedIdxs[i+shift] - 1;
                }
            }
            const rssi_t v = e.rssi;
            const int_fast8_t idx = UnifiedSendBuffer<Extremum,N>::buffer.size()-1;
            int_fast8_t j = idx-1;
            for (; j>=0 && UnifiedSendBuffer<Extremum,N>::buffer[sortedIdxs[j]].rssi > v; j--) {
                sortedIdxs[j+1] = sortedIdxs[j];
            }
            sortedIdxs[j+1] = idx;
            return hadCapacity;
        }

    public:
        void removeLast() {
            UnifiedSendBuffer<Extremum,N>::removeLast();
            const int_fast8_t lastIdx = UnifiedSendBuffer<Extremum,N>::buffer.size();
            int_fast8_t shift = 0;
            for (int_fast8_t i=0; i<lastIdx; i++) {
                if (sortedIdxs[i] == lastIdx) {
                    shift = 1;
                }
                sortedIdxs[i] = sortedIdxs[i+shift];
            }
        }
};
#endif
