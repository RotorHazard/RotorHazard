#include "config.h"
#if TARGET == ESP32_TARGET
#include "esp32_hardware.h"

Esp32Hardware defaultHardware;
Hardware& hardware = defaultHardware;

static Message serialMessage;

void serialEvent()
{
    handleStreamEvent(SERIALCOM, serialMessage);
}

void serialEventRun()
{
    if (SERIALCOM.available())
    {
        serialEvent();
    }
}
#endif
