#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "microclock.h"

unittest(clock_offset)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    nano->micros = 20000;
    // create clock at non-zero system time
    MicroClock clock;
    assertEqual(20000, clock.tickMicros());
    assertEqual(20, clock.millis());
}

unittest(clock_under)
{
  GodmodeState* nano = GODMODE();
  nano->reset();
  MicroClock clock;
  nano->micros = 400;
  assertEqual(400, clock.tickMicros());
  assertEqual(0, clock.millis());
  nano->micros = 1000;
  assertEqual(1000, clock.tickMicros());
  assertEqual(1, clock.millis());
  nano->micros = 1800;
  assertEqual(1800, clock.tickMicros());
  assertEqual(1, clock.millis());
}

unittest(clock_over)
{
  GodmodeState* nano = GODMODE();
  nano->reset();
  MicroClock clock;
  nano->micros = 1500;
  assertEqual(1500, clock.tickMicros());
  assertEqual(1, clock.millis());
  nano->micros = 3000;
  assertEqual(3000, clock.tickMicros());
  assertEqual(3, clock.millis());
  nano->micros = 4500;
  assertEqual(4500, clock.tickMicros());
  assertEqual(4, clock.millis());
}

unittest(clock_rollover)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    MicroClock clock;
    const utime_t maxMicros = 0xFFFFFFFF;
    const mtime_t maxMicrosInMillis = maxMicros/1000;
    nano->micros = maxMicros;
    assertEqual(maxMicros, clock.tickMicros());
    nano->micros = 1000;
    assertEqual(1000, clock.tickMicros());
    assertEqual(maxMicrosInMillis+1, clock.millis());
}

unittest_main()
