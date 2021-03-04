#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "microclock.h"

unittest(clock_offset)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    nano->micros = 20000;
    MicroClock clock;
    assertEqual(0, clock.tick());
}

unittest(clock_under)
{
  GodmodeState* nano = GODMODE();
  nano->reset();
  MicroClock clock;
  nano->micros = 400;
  assertEqual(400, clock.tick());
  assertEqual(0, clock.millis());
  nano->micros = 1000;
  assertEqual(600, clock.tick());
  assertEqual(1, clock.millis());
  nano->micros = 1800;
  assertEqual(800, clock.tick());
  assertEqual(1, clock.millis());
}

unittest(clock_over)
{
  GodmodeState* nano = GODMODE();
  nano->reset();
  MicroClock clock;
  nano->micros = 1500;
  assertEqual(1500, clock.tick());
  assertEqual(1, clock.millis());
  nano->micros = 3000;
  assertEqual(1500, clock.tick());
  assertEqual(3, clock.millis());
  nano->micros = 4500;
  assertEqual(1500, clock.tick());
  assertEqual(4, clock.millis());
}

unittest(clock_rollover)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    MicroClock clock;
    nano->micros = 0xFFFFFFFF;
    assertEqual(0xFFFFFFFF, clock.tick());
    nano->micros = 1000;
    assertEqual(1001, clock.tick());
    assertEqual(0xFFFFFFFF/1000+1, clock.millis());
}

unittest_main()
