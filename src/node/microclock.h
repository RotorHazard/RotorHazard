// NB: filename avoids conflict with stm32 clock.h
#ifndef microclock_h
#define microclock_h

#include "config.h"

/*** Microsecond accurate millisecond clock. */
class MicroClock
{
#if TARGET != STM32_TARGET
private:
    utime_t prevTick = 0;
    volatile mtime_t timeMillis = 0;
    volatile uint16_t excessMicros = 0;
#endif
public:
    utime_t tickMicros();
    mtime_t millis();
};

extern MicroClock usclock;

#endif
