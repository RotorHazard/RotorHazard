#include "config.h"
#if TARGET == STM32_TARGET
#include "stm32_hardware.h"

Stm32Hardware defaultHardware;
Hardware& hardware = defaultHardware;

static Message serialMessage;

void serialEvent()
{
    handleStreamEvent(SERIALCOM, serialMessage);
}
#endif
