#include "config.h"
#if STM32_MODE_FLAG
#include "stm32_hardware.h"

Stm32Hardware defaultHardware;
Hardware *hardware = &defaultHardware;

static Message serialMessage(RssiReceivers::rssiRxs, hardware);

void serialEvent()
{
    handleStreamEvent(SERIALCOM, serialMessage);
}
#endif
