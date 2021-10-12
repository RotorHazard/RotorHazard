#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rx.h"

unittest(bitbang_powerUp)
{
    BitBangRxModule rx;
    rx.powerUp();
    assertFalse(rx.isPoweredDown());
}

unittest(bitbang_powerDown)
{
    BitBangRxModule rx;
    rx.powerDown();
    assertTrue(rx.isPoweredDown());
}

unittest_main()
