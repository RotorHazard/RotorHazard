#ifndef PERSISTENT_HOMOLOGY_H
#define PERSISTENT_HOMOLOGY_H
#include "rhtypes.h"
#include "Collections.h"

struct ConnectedComponent {
    uint8_t birth = 0;
    uint8_t death = 0;
    inline uint_fast8_t peakLifetime(rssi_t phData[]) {
        return phData[birth] - phData[death];
    }
    inline uint_fast8_t nadirLifetime(rssi_t phData[]) {
        return phData[death] - phData[birth];
    }
};

template <size_t N> static ConnectedComponent *idxToCC[N];

template <typename T> static void sort(const T pns[], uint_fast8_t sortedIdxs[], const uint_fast8_t size) {
    // insertion sort
    for (uint_fast8_t i=1; i<size; i++) {
        const uint_fast8_t idx = sortedIdxs[i];
        const T v = pns[idx];
        int_fast8_t j = i-1;
        for (; j>=0 && pns[sortedIdxs[j]] > v; j--) {
            sortedIdxs[j+1] = sortedIdxs[j];
        }
        sortedIdxs[j+1] = idx;
    }
}

template <typename T, size_t N> uint_fast8_t calculatePeakPersistentHomology(const T pns[], const uint_fast8_t sortedIdxs[], const uint_fast8_t size, ConnectedComponent ccs[], int_fast8_t *idxPtr = nullptr) {
    static_assert(N <= 127, "can't exceed 127 - 7-bit indices");

    ExtremumType firstType;
    ExtremumType altType;
    if (size < 2 || pns[0] > pns[1]) {
        firstType = PEAK;
        altType = NADIR;
    } else {
        firstType = NADIR;
        altType = PEAK;
    }

    const uint_fast8_t minIdx = sortedIdxs[0];
    uint_fast8_t ccCount = 0;
    for (int_fast8_t i=size-1; i>=0; i--) {
        const uint_fast8_t idx = sortedIdxs[i];
        const ExtremumType etype = idx&1 ? altType : firstType;
        if (etype == PEAK) {
            // peak
            ConnectedComponent& cc = ccs[ccCount];
            cc.birth = idx;
            cc.death = minIdx;
            idxToCC<N>[idx] = &cc;
            if (idxPtr && *idxPtr == idx) {
                *idxPtr = -ccCount-1;
            }
            ccCount++;
        } else {
            // nadir
            ConnectedComponent *leftCC = (idx > 0) ? idxToCC<N>[idx-1] : nullptr;
            ConnectedComponent *rightCC = (idx < size-1) ? idxToCC<N>[idx+1] : nullptr;
            if (leftCC != nullptr && rightCC != nullptr) {
                if (pns[leftCC->birth] > pns[rightCC->birth]) {
                    // merge right into left
                    rightCC->death = idx;
                    idxToCC<N>[idx+1] = idxToCC<N>[idx-1];
                } else {
                    // merge left into right
                    leftCC->death = idx;
                    idxToCC<N>[idx-1] = idxToCC<N>[idx+1];
                }
            }
        }
    }
    return ccCount;
}

template <typename T, size_t N> uint_fast8_t calculateNadirPersistentHomology(const T pns[], const uint_fast8_t sortedIdxs[], uint_fast8_t size, ConnectedComponent ccs[], int_fast8_t *idxPtr = nullptr) {
    static_assert(N <= 127, "can't exceed 127 - 7-bit indices");

    ExtremumType firstType;
    ExtremumType altType;
    if (size < 2 || pns[0] > pns[1]) {
        firstType = PEAK;
        altType = NADIR;
    } else {
        firstType = NADIR;
        altType = PEAK;
    }

    const uint_fast8_t maxIdx = sortedIdxs[size-1];
    uint_fast8_t ccCount = 0;
    for (int_fast8_t i=0; i<size; i++) {
        const uint_fast8_t idx = sortedIdxs[i];
        const ExtremumType etype = idx&1 ? altType : firstType;
        if (etype == PEAK) {
            // peak
            ConnectedComponent *leftCC = (idx > 0) ? idxToCC<N>[idx-1] : nullptr;
            ConnectedComponent *rightCC = (idx < size-1) ? idxToCC<N>[idx+1] : nullptr;
            if (leftCC != nullptr && rightCC != nullptr) {
                if (pns[leftCC->birth] < pns[rightCC->birth]) {
                    // merge right into left
                    rightCC->death = idx;
                    idxToCC<N>[idx+1] = idxToCC<N>[idx-1];
                } else {
                    // merge left into right
                    leftCC->death = idx;
                    idxToCC<N>[idx-1] = idxToCC<N>[idx+1];
                }
            }
        } else {
            // nadir
            ConnectedComponent& cc = ccs[ccCount];
            cc.birth = idx;
            cc.death = maxIdx;
            idxToCC<N>[idx] = &cc;
            if (idxPtr && *idxPtr == idx) {
                *idxPtr = -ccCount-1;
            }
            ccCount++;
        }
    }
    return ccCount;
}
#endif
