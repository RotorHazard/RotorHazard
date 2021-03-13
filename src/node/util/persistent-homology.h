#ifndef PERSISTENT_HOMOLOGY_H
#define PERSISTENT_HOMOLOGY_H
#include "rhtypes.h"
#include "Collections.h"

struct ConnectedComponent {
    uint_fast8_t birth = 0;
    uint_fast8_t death = 0;
};

template <size_t N> static ConnectedComponent *idxToCC[N];
template <size_t N> static uint_fast8_t sortedIdxs[N];

template <typename T, size_t N> uint_fast8_t calculatePeakPersistentHomology(const T pns[], const uint_fast8_t size, ConnectedComponent ccs[], int_fast8_t *idxPtr = nullptr) {
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

    // initialisation & pre-sort
    for (uint_fast8_t i=0; i<size; i++) {
        idxToCC<N>[i] = nullptr;
        ExtremumType t = i&1 ? altType : firstType;
        if (t == PEAK) {
            sortedIdxs<N>[(i+size)/2] = i;
        } else {
            sortedIdxs<N>[i/2] = i;
        }
    }

    // insertion sort
    for (uint_fast8_t i=1; i<size; i++) {
        const uint_fast8_t idx = sortedIdxs<N>[i];
        const T v = pns[idx];
        int_fast8_t j = i-1;
        for (; j>=0 && pns[sortedIdxs<N>[j]] > v; j--) {
            sortedIdxs<N>[j+1] = sortedIdxs<N>[j];
        }
        sortedIdxs<N>[j+1] = idx;
    }

    const uint_fast8_t minIdx = sortedIdxs<N>[0];
    uint_fast8_t ccCount = 0;
    for (int_fast8_t i=size-1; i>=0; i--) {
        const uint_fast8_t idx = sortedIdxs<N>[i];
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

template <typename T, size_t N> uint_fast8_t calculateNadirPersistentHomology(const T pns[], uint_fast8_t size, ConnectedComponent ccs[], int_fast8_t *idxPtr = nullptr) {
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

    // initialisation & pre-sort
    for (uint_fast8_t i=0; i<size; i++) {
        idxToCC<N>[i] = nullptr;
        ExtremumType t = i&1 ? altType : firstType;
        if (t == NADIR) {
            sortedIdxs<N>[(i+size)/2] = i;
        } else {
            sortedIdxs<N>[i/2] = i;
        }
    }

    // insertion sort
    for (uint_fast8_t i=1; i<size; i++) {
        const uint_fast8_t idx = sortedIdxs<N>[i];
        const T v = pns[idx];
        int_fast8_t j = i-1;
        for (; j>=0 && pns[sortedIdxs<N>[j]] < v; j--) {
            sortedIdxs<N>[j+1] = sortedIdxs<N>[j];
        }
        sortedIdxs<N>[j+1] = idx;
    }

    const uint_fast8_t maxIdx = sortedIdxs<N>[0];
    uint_fast8_t ccCount = 0;
    for (int_fast8_t i=size-1; i>=0; i--) {
        const uint_fast8_t idx = sortedIdxs<N>[i];
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
