#include <ArduinoUnitTests.h>
#include "util/persistent-homology.h"

#define pn_size(arr) (sizeof(arr)/sizeof(rssi_t))

unittest(ph_peak)
{
    rssi_t testData[13] = {
        30,
        29,
        41,
        4,
        114,
        1,
        3,
        2,
        33,
        9,
        112,
        40,
        118
    };
    ConnectedComponent ccs[(pn_size(testData)+1)/2];
    uint_fast8_t numCCs = calculatePeakPersistentHomology<rssi_t,pn_size(testData)>(testData, pn_size(testData), ccs);
    assertEqual(7, numCCs);
    uint8_t expectedBirths[] = {12, 4, 10, 2, 8, 0, 6};
    uint8_t expectedDeaths[] = {5, 5, 11, 3, 9, 1, 7};
    rssi_t expectedBirthRssis[] = {118, 114, 112, 41, 33, 30, 3};
    rssi_t expectedDeathRssis[] = {1, 1, 40, 4, 9, 29, 2};
    for (int i=0; i<numCCs; i++) {
        assertEqual(expectedBirths[i], ccs[i].birth);
        assertEqual(expectedDeaths[i], ccs[i].death);
        rssi_t peak = testData[ccs[i].birth];
        assertEqual(expectedBirthRssis[i], peak);
        rssi_t nadir = testData[ccs[i].death];
        assertEqual(expectedDeathRssis[i], nadir);
    }

    int_fast8_t peakIdx = 4;
    calculatePeakPersistentHomology<rssi_t,pn_size(testData)>(testData, pn_size(testData), ccs, &peakIdx);
    assertEqual(-2, peakIdx);
    int_fast8_t nadirIdx = 7;
    calculatePeakPersistentHomology<rssi_t,pn_size(testData)>(testData, pn_size(testData), ccs, &nadirIdx);
    assertEqual(7, nadirIdx);
}

unittest(ph_nadir)
{
    rssi_t testData[13] = {
        225,
        226,
        214,
        251,
        141,
        254,
        252,
        253,
        222,
        246,
        143,
        215,
        137
    };
    ConnectedComponent ccs[(pn_size(testData)+1)/2];
    uint_fast8_t numCCs = calculateNadirPersistentHomology<rssi_t,pn_size(testData)>(testData, pn_size(testData), ccs);
    assertEqual(7, numCCs);
    uint8_t expectedBirths[] = {12, 4, 10, 2, 8, 0, 6};
    uint8_t expectedDeaths[] = {5, 5, 11, 3, 9, 1, 7};
    rssi_t expectedBirthRssis[] = {137, 141, 143, 214, 222, 225, 252};
    rssi_t expectedDeathRssis[] = {254, 254, 215, 251, 246, 226, 253};
    for (int i=0; i<numCCs; i++) {
        assertEqual(expectedBirths[i], ccs[i].birth);
        assertEqual(expectedDeaths[i], ccs[i].death);
        rssi_t peak = testData[ccs[i].birth];
        assertEqual(expectedBirthRssis[i], peak);
        rssi_t nadir = testData[ccs[i].death];
        assertEqual(expectedDeathRssis[i], nadir);
    }

    int_fast8_t nadirIdx = 4;
    calculateNadirPersistentHomology<rssi_t,pn_size(testData)>(testData, pn_size(testData), ccs, &nadirIdx);
    assertEqual(-2, nadirIdx);
    int_fast8_t peakIdx = 7;
    calculateNadirPersistentHomology<rssi_t,pn_size(testData)>(testData, pn_size(testData), ccs, &peakIdx);
    assertEqual(7, peakIdx);
}

unittest(ph_degenerate)
{
    rssi_t testData[4] = {
        220,
        120,
        220,
        120
    };
    ConnectedComponent ccs[(pn_size(testData)+1)/2];
    uint_fast8_t numCCs = calculatePeakPersistentHomology<rssi_t,pn_size(testData)>(testData, pn_size(testData), ccs);
    assertEqual(2, numCCs);
    uint8_t expectedBirths[] = {2, 0};
    uint8_t expectedDeaths[] = {1, 1};
    rssi_t expectedBirthRssis[] = {220, 220};
    rssi_t expectedDeathRssis[] = {120, 120};
    for (int i=0; i<numCCs; i++) {
        assertEqual(expectedBirths[i], ccs[i].birth);
        assertEqual(expectedDeaths[i], ccs[i].death);
        rssi_t peak = testData[ccs[i].birth];
        assertEqual(expectedBirthRssis[i], peak);
        rssi_t nadir = testData[ccs[i].death];
        assertEqual(expectedDeathRssis[i], nadir);
    }
}

unittest_main()
