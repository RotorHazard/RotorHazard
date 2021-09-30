#ifndef rhtypes_h
#define rhtypes_h

#include <inttypes.h>

// semantic types
typedef uint32_t mtime_t; // milliseconds
typedef uint32_t utime_t; // microseconds
typedef uint8_t rssi_t;
typedef uint16_t freq_t; // MHz

enum ExtremumType: int8_t {
    PEAK = 1,
    NADIR = -1,
    NONE = 0
};

struct Extremum
{
  rssi_t volatile rssi;
  mtime_t volatile firstTime;
  uint16_t volatile duration;
};

struct FreqRssi
{
    freq_t volatile freq;
    rssi_t volatile rssi;
};

constexpr rssi_t MAX_RSSI = 0xFF;
bool isPeakValid(const Extremum& x);
bool isNadirValid(const Extremum& x);
void invalidatePeak(Extremum& x);
void invalidateNadir(Extremum& x);
rssi_t rssiValue(const Extremum& x);
mtime_t endTime(const Extremum& x);

#endif
