#include "config.h"
#include "microclock.h"

MicroClock usclock;

MicroClock::MicroClock() : prevTick(micros()) {
}

uint32_t MicroClock::tick()
{
    utime_t currentTick = micros();
    // unsigned arithmetic to handle roll-over
    uint32_t elapsed = currentTick - prevTick;
    uint32_t delta = elapsed + excessMicros;
    uint32_t deltaMillis = delta/1000;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        timeMillis += deltaMillis;
        excessMicros = delta - deltaMillis*1000;
    }
    prevTick = currentTick;
    return elapsed;
}

mtime_t MicroClock::millis()
{
    return timeMillis;
}
