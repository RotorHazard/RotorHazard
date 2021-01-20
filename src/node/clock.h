#ifndef clock_h
#define clock_h

#include "util/rhtypes.h"

class Clock
{
private:
    utime_t prevTick = 0;
    volatile mtime_t timeMillis = 0;
    volatile uint16_t excessMicros = 0;
public:
    /**
     * Returns elapsed microseconds since last tick.
     */
    uint32_t tick();
    mtime_t millis();
};

extern Clock usclock;

#endif
