#ifndef rhtypes_h
#define rhtypes_h

#include <inttypes.h>

// semantic types
typedef uint32_t mtime_t; // milliseconds
typedef uint32_t utime_t; // micros
typedef uint8_t rssi_t;
typedef uint16_t freq_t; // MHz

enum ExtremumType {
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
    freq_t freq;
    rssi_t rssi;
};

constexpr rssi_t MAX_RSSI = 0xFF;
inline bool isPeakValid(const Extremum& x) { return x.rssi != 0; }
inline bool isNadirValid(const Extremum& x) { return x.rssi != MAX_RSSI; }
inline void invalidatePeak(Extremum& x) { x.rssi = 0; }
inline void invalidateNadir(Extremum& x) { x.rssi = MAX_RSSI; }
inline mtime_t endTime(const Extremum& x) { return x.firstTime + x.duration; }

#endif
