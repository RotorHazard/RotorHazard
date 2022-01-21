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

        const int_fast8_t findNextBestPeak(int_fast8_t startPeakIdx) const {
            int_fast8_t bestIdx = startPeakIdx;
            T bestValue = buffer[bestIdx];
            for (int_fast8_t i = bestIdx+2; i<buffer.size(); i+=2) {
                const T& value = buffer[i];
                if (value > bestValue) {
                    bestIdx = i;
                    bestValue = value;
                }
            }
            return bestIdx;
        }

        const int_fast8_t findNextBestNadir(int_fast8_t startNadirIdx) const {
            int_fast8_t bestIdx = startNadirIdx;
            T bestValue = buffer[bestIdx];
            for (int_fast8_t i = bestIdx+2; i<buffer.size(); i+=2) {
                const T& value = buffer[i];
                if (value < bestValue) {
                    bestIdx = i;
                    bestValue = value;
                }
            }
            return bestIdx;
        }

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
        const T firstAvailable() const {
            return buffer[nextToSendIndex];
        }
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
        const T nextPeak() const {
            int_fast8_t nextIdx;
            if (nextType() == NADIR && remainingToSend() > 1) {
                nextIdx = findNextBestPeak(nextToSendIndex+1);
            } else {
                nextIdx = findNextBestPeak(nextToSendIndex);
            }
            return buffer[nextIdx];
        }
        const T nextNadir() const {
            int_fast8_t nextIdx;
            if (nextType() == PEAK && remainingToSend() > 1) {
                nextIdx = findNextBestNadir(nextToSendIndex+1);
            } else {
                nextIdx = findNextBestNadir(nextToSendIndex);
            }
            return buffer[nextIdx];
        }
        const ExtremumType nextType() const {
            return remainingToSend() > 0 ? typeAt(nextToSendIndex) : NONE;
        }
        const T popNext() {
            int_fast8_t nextIdx;
            const ExtremumType t = nextType();
            switch(t) {
                case PEAK:
                    nextIdx = findNextBestPeak(nextToSendIndex);
                    nextToSendIndex = nextIdx + 1;
                    break;
                case NADIR:
                    nextIdx = findNextBestNadir(nextToSendIndex);
                    nextToSendIndex = nextIdx + 1;
                    break;
                default:
                    nextIdx = nextToSendIndex;
            }
            return buffer[nextIdx];
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

template <typename T, uint8_t N> class SortedUnifiedSendBuffer : public UnifiedSendBuffer<T,N> {
    public:
        uint_fast8_t sortedIdxs[N];

    protected:
        bool add(const T& e) {
            bool hadCapacity = UnifiedSendBuffer<T,N>::add(e);
            if (!hadCapacity) {
                const int_fast8_t lastIdx = UnifiedSendBuffer<T,N>::buffer.size() - 1;
                int_fast8_t shift = 0;
                for (int_fast8_t i=0; i<lastIdx; i++) {
                    if (sortedIdxs[i] == 0) {
                        shift = 1;
                    }
                    sortedIdxs[i] = sortedIdxs[i+shift] - 1;
                }
            }
            const int_fast8_t idx = UnifiedSendBuffer<T,N>::buffer.size() - 1;
            int_fast8_t j = idx - 1;
            for (; j>=0 && UnifiedSendBuffer<T,N>::buffer[sortedIdxs[j]] > e; j--) {
                sortedIdxs[j+1] = sortedIdxs[j];
            }
            sortedIdxs[j+1] = idx;
            return hadCapacity;
        }

    public:
        void copyRssi(rssi_t* out) const {
            UnifiedSendBuffer<T,N>::buffer.copyTo(out, rssiValue);
        }
        void removeLast() {
            UnifiedSendBuffer<T,N>::removeLast();
            const int_fast8_t lastIdx = UnifiedSendBuffer<T,N>::buffer.size();
            int_fast8_t shift = 0;
            int_fast8_t i = 0;
            for (; i<lastIdx; i++) {
                if (sortedIdxs[i] == lastIdx) {
                    shift = 1;
                    break;
                }
            }
            if (shift > 0) {
                for (; i<lastIdx; i++) {
                    sortedIdxs[i] = sortedIdxs[i+shift];
                }
            }
        }
};
#endif
