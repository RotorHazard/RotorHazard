#ifndef PERSISTENT_HOMOLOGY_H
#define PERSISTENT_HOMOLOGY_H
#include "rhtypes.h"
#include "Collections.h"

struct ConnectedComponent {
    uint8_t birth;
    uint8_t death;
};

template <size_t N> uint8_t calculatePeakPersistentHomology(const List<Extremum,N>& pns, const ExtremumType firstType, ConnectedComponent ccs[], int8_t *idxPtr = nullptr) {
    static_assert(N <= 127, "can't exceed 127 - 7-bit indices");
    ConnectedComponent *idxToCC[N];
    uint8_t sortedIdxs[N];

    const uint8_t size = pns.size();
    for (int8_t i=size-1; i>=0; i--) {
        idxToCC[i] = nullptr;
        sortedIdxs[i] = i;
    }

    for (uint8_t i=1; i<size; i++) {
        const uint8_t idx = sortedIdxs[i];
        const rssi_t r = pns[idx].rssi;
        int8_t j = i-1;
        for (; j>=0 && pns[sortedIdxs[j]].rssi > r; j--) {
            sortedIdxs[j+1] = sortedIdxs[j];
        }
        sortedIdxs[j+1] = idx;
    }

    const uint8_t minIdx = sortedIdxs[0];
    const ExtremumType altType = (firstType == PEAK) ? NADIR : PEAK;
    uint8_t ccCount = 0;
    for (int8_t i=size-1; i>=0; i--) {
        const uint8_t idx = sortedIdxs[i];
        const ExtremumType etype = idx&1 ? altType : firstType;
        if (etype == PEAK) {
            // peak
            ConnectedComponent& cc = ccs[ccCount];
            cc.birth = idx;
            cc.death = minIdx;
            idxToCC[idx] = &cc;
            if (idxPtr && *idxPtr == idx) {
                *idxPtr = -ccCount-1;
            }
            ccCount++;
        } else {
            // nadir
            ConnectedComponent *leftCC = (idx > 0) ? idxToCC[idx-1] : nullptr;
            ConnectedComponent *rightCC = (idx < size-1) ? idxToCC[idx+1] : nullptr;
            if (leftCC != nullptr && rightCC != nullptr) {
                if (pns[leftCC->birth].rssi > pns[rightCC->birth].rssi) {
                    // merge right into left
                    rightCC->death = idx;
                    idxToCC[idx+1] = idxToCC[idx-1];
                } else {
                    // merge left into right
                    leftCC->death = idx;
                    idxToCC[idx-1] = idxToCC[idx+1];
                }
            }
        }
    }
    return ccCount;
}

template <size_t N> uint8_t calculateNadirPersistentHomology(const List<Extremum,N>& pns, const ExtremumType firstType, ConnectedComponent ccs[], int8_t *idxPtr = nullptr) {
    static_assert(N <= 127, "can't exceed 127 - 7-bit indices");
    ConnectedComponent *idxToCC[N];
    uint8_t sortedIdxs[N];

    const uint8_t size = pns.size();
    for (int8_t i=size-1; i>=0; i--) {
        idxToCC[i] = nullptr;
        sortedIdxs[i] = i;
    }

    for (uint8_t i=1; i<size; i++) {
        const uint8_t idx = sortedIdxs[i];
        const rssi_t r = pns[idx].rssi;
        int8_t j = i-1;
        for (; j>=0 && pns[sortedIdxs[j]].rssi < r; j--) {
            sortedIdxs[j+1] = sortedIdxs[j];
        }
        sortedIdxs[j+1] = idx;
    }

    const uint8_t maxIdx = sortedIdxs[0];
    const ExtremumType altType = (firstType == PEAK) ? NADIR : PEAK;
    uint8_t ccCount = 0;
    for (int8_t i=size-1; i>=0; i--) {
        const uint8_t idx = sortedIdxs[i];
        const ExtremumType etype = idx&1 ? altType : firstType;
        if (etype == PEAK) {
            // peak
            ConnectedComponent *leftCC = (idx > 0) ? idxToCC[idx-1] : nullptr;
            ConnectedComponent *rightCC = (idx < size-1) ? idxToCC[idx+1] : nullptr;
            if (leftCC != nullptr && rightCC != nullptr) {
                if (pns[leftCC->birth].rssi < pns[rightCC->birth].rssi) {
                    // merge right into left
                    rightCC->death = idx;
                    idxToCC[idx+1] = idxToCC[idx-1];
                } else {
                    // merge left into right
                    leftCC->death = idx;
                    idxToCC[idx-1] = idxToCC[idx+1];
                }
            }
        } else {
            // nadir
            ConnectedComponent& cc = ccs[ccCount];
            cc.birth = idx;
            cc.death = maxIdx;
            idxToCC[idx] = &cc;
            if (idxPtr && *idxPtr == idx) {
                *idxPtr = -ccCount-1;
            }
            ccCount++;
        }
    }
    return ccCount;
}
#endif
