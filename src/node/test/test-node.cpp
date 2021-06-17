#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "test_hardware.h"

extern void setup();
extern void loop();

unittest(lifecycle)
{
  GodmodeState* nano = GODMODE();
  nano->reset();
  setup();
  assertTrue(testHardware.isInit);
  assertTrue(testHardware.isRxInit[0]);
  assertTrue(testHardware.isSettingsInit[0]);
  for(int i=0; i<1000; i++) {
      loop();
      nano->micros += 10*1000;
  }
}

unittest_main()
