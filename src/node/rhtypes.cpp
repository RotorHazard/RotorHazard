#include "util/rhtypes.h"

bool isPeakValid(const Extremum& x) { return x.rssi != 0; }
bool isNadirValid(const Extremum& x) { return x.rssi != MAX_RSSI; }
void invalidatePeak(Extremum& x) { x.rssi = 0; }
void invalidateNadir(Extremum& x) { x.rssi = MAX_RSSI; }
rssi_t rssiValue(const Extremum& x) { return x.rssi; }
mtime_t endTime(const Extremum& x) { return x.firstTime + x.duration; }
