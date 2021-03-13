#include "microclock.h"

MicroClock usclock;

utime_t MicroClock::tickMicros()
{
#if TARGET != STM32_TARGET
    const utime_t currentTick = ::micros();
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
    return currentTick;
#else
    return ::micros();
#endif
}

mtime_t MicroClock::millis()
{
#if TARGET != STM32_TARGET
    return timeMillis;
#else
    // native impl is sufficiently accurate
    return ::millis();
#endif
}
