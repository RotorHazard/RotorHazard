#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "clock.h"

unittest(clock_under)
{
  GodmodeState* nano = GODMODE();
  nano->reset();
  nano->micros = 400;
  Clock clock;
  assertEqual(400, clock.tick());
  assertEqual(0, clock.millis());
  nano->micros = 1000;
  assertEqual(600, clock.tick());
  assertEqual(1, clock.millis());
}

unittest(clock_over)
{
  GodmodeState* nano = GODMODE();
  nano->reset();
  nano->micros = 1500;
  Clock clock;
  assertEqual(1500, clock.tick());
  assertEqual(1, clock.millis());
  nano->micros = 3000;
  assertEqual(1500, clock.tick());
  assertEqual(3, clock.millis());
}

unittest(clock_rollover)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    nano->micros = 0xFFFFFFFF;
    Clock clock;
    assertEqual(0xFFFFFFFF, clock.tick());
    nano->micros = 1000;
    assertEqual(1001, clock.tick());
    assertEqual(0xFFFFFFFF/1000+1, clock.millis());
}

unittest_main()
