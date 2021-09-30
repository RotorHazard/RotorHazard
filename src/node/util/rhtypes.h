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
  rssi_t rssi;
  mtime_t firstTime;
  uint16_t duration;
};

struct FreqRssi
{
    freq_t freq;
    rssi_t rssi;
};

constexpr rssi_t MAX_RSSI = 0xFF;
constexpr bool isPeakValid(const Extremum& x) { return x.rssi != 0; }
constexpr bool isNadirValid(const Extremum& x) { return x.rssi != MAX_RSSI; }
inline void invalidatePeak(Extremum& x) { x.rssi = 0; }
inline void invalidateNadir(Extremum& x) { x.rssi = MAX_RSSI; }
constexpr rssi_t rssiValue(const Extremum& x) { return x.rssi; }
constexpr mtime_t endTime(const Extremum& x) { return x.firstTime + x.duration; }

#endif
