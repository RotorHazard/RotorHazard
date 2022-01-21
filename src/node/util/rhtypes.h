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
    bool equals(Extremum const& rhs) const {
        return rssi == rhs.rssi && firstTime == rhs.firstTime && duration == rhs.duration;
    };
    bool lessThan(Extremum const& rhs) const {
        return rssi < rhs.rssi;
    };
};

inline bool operator==(Extremum const& lhs, Extremum const& rhs) {
    return lhs.equals(rhs);
}
inline bool operator<(Extremum const& lhs, Extremum const& rhs) {
    return lhs.lessThan(rhs);
}
inline bool operator!=(Extremum const& lhs, Extremum const& rhs) {
    return !operator==(lhs, rhs);
}
inline bool operator>(Extremum const& lhs, Extremum const& rhs) {
    return operator<(rhs, lhs);
}
inline bool operator<=(Extremum const& lhs, Extremum const& rhs) {
    return !operator<(rhs, lhs);
}
inline bool operator>=(Extremum const& lhs, Extremum const& rhs) {
    return !operator<(lhs, rhs);
}

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
