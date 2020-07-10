#ifndef rhtypes_h
#define rhtypes_h

#include <inttypes.h>

// semantic types
typedef uint32_t mtime_t; // milliseconds
typedef uint32_t utime_t; // micros
typedef uint8_t rssi_t;

struct Extremum
{
  rssi_t volatile rssi;
  mtime_t volatile firstTime;
  uint16_t volatile duration;
};

#define MAX_RSSI 0xFF
#define isPeakValid(x) ((x).rssi != 0)
#define isNadirValid(x) ((x).rssi != MAX_RSSI)
#define invalidatePeak(x) ((x).rssi = 0)
#define invalidateNadir(x) ((x).rssi = MAX_RSSI)

#endif
