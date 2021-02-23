#include <ArduinoUnitTests.h>
#include "util/persistent-homology.h"
#include "util/Lists.h"

unittest(ph_peak)
{
    Extremum testData[13] = {
        {30, 0},
        {29, 2},
        {41, 4},
        {4, 6},
        {114, 8},
        {1, 10},
        {3, 12},
        {2, 14},
        {33, 16},
        {9, 18},
        {112, 20},
        {40, 22},
        {118, 24}
    };
    ArrayList<Extremum,13> buffer(testData);
    ConnectedComponent ccs[(13+1)/2];
    uint8_t numCCs = calculatePeakPersistentHomology(buffer, PEAK, ccs);
    assertEqual(7, numCCs);
    uint8_t expectedBirths[] = {12, 4, 10, 2, 8, 0, 6};
    uint8_t expectedDeaths[] = {5, 5, 11, 3, 9, 1, 7};
    rssi_t expectedBirthRssis[] = {118, 114, 112, 41, 33, 30, 3};
    rssi_t expectedDeathRssis[] = {1, 1, 40, 4, 9, 29, 2};
    for (int i=0; i<numCCs; i++) {
        assertEqual(expectedBirths[i], ccs[i].birth);
        assertEqual(expectedDeaths[i], ccs[i].death);
        Extremum peak = buffer[ccs[i].birth];
        assertEqual(expectedBirthRssis[i], peak.rssi);
        Extremum nadir = buffer[ccs[i].death];
        assertEqual(expectedDeathRssis[i], nadir.rssi);
    }

    int8_t peakIdx = 4;
    calculatePeakPersistentHomology(buffer, PEAK, ccs, &peakIdx);
    assertEqual(-2, peakIdx);
    int8_t nadirIdx = 7;
    calculatePeakPersistentHomology(buffer, PEAK, ccs, &nadirIdx);
    assertEqual(7, nadirIdx);
}

unittest(ph_nadir)
{
    Extremum testData[13] = {
        {225, 0},
        {226, 2},
        {214, 4},
        {251, 6},
        {141, 8},
        {254, 10},
        {252, 12},
        {253, 14},
        {222, 16},
        {246, 18},
        {143, 20},
        {215, 22},
        {137, 24}
    };
    ArrayList<Extremum,13> buffer(testData);
    ConnectedComponent ccs[(13+1)/2];
    uint8_t numCCs = calculateNadirPersistentHomology(buffer, NADIR, ccs);
    assertEqual(7, numCCs);
    uint8_t expectedBirths[] = {12, 4, 10, 2, 8, 0, 6};
    uint8_t expectedDeaths[] = {5, 5, 11, 3, 9, 1, 7};
    rssi_t expectedBirthRssis[] = {137, 141, 143, 214, 222, 225, 252};
    rssi_t expectedDeathRssis[] = {254, 254, 215, 251, 246, 226, 253};
    for (int i=0; i<numCCs; i++) {
        assertEqual(expectedBirths[i], ccs[i].birth);
        assertEqual(expectedDeaths[i], ccs[i].death);
        Extremum peak = buffer[ccs[i].birth];
        assertEqual(expectedBirthRssis[i], peak.rssi);
        Extremum nadir = buffer[ccs[i].death];
        assertEqual(expectedDeathRssis[i], nadir.rssi);
    }

    int8_t nadirIdx = 4;
    calculateNadirPersistentHomology(buffer, NADIR, ccs, &nadirIdx);
    assertEqual(-2, nadirIdx);
    int8_t peakIdx = 7;
    calculateNadirPersistentHomology(buffer, NADIR, ccs, &peakIdx);
    assertEqual(7, peakIdx);
}

unittest(ph_degenerate)
{
    Extremum testData[4] = {
        {220, 0},
        {120, 2},
        {220, 4},
        {120, 6}
    };
    ArrayList<Extremum,4> buffer(testData);
    ConnectedComponent ccs[(4+1)/2];
    uint8_t numCCs = calculatePeakPersistentHomology(buffer, PEAK, ccs);
    assertEqual(2, numCCs);
    uint8_t expectedBirths[] = {2, 0};
    uint8_t expectedDeaths[] = {1, 1};
    rssi_t expectedBirthRssis[] = {220, 220};
    rssi_t expectedDeathRssis[] = {120, 120};
    for (int i=0; i<numCCs; i++) {
        assertEqual(expectedBirths[i], ccs[i].birth);
        assertEqual(expectedDeaths[i], ccs[i].death);
        Extremum peak = buffer[ccs[i].birth];
        assertEqual(expectedBirthRssis[i], peak.rssi);
        Extremum nadir = buffer[ccs[i].death];
        assertEqual(expectedDeathRssis[i], nadir.rssi);
    }
}

unittest_main()
