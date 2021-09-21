#include "config.h"
#if TARGET == ESP8266_TARGET
#include "esp8266_hardware.h"

Esp8266Hardware defaultHardware;
Hardware& hardware = defaultHardware;

static Message serialMessage;

void serialEvent()
{
    handleStreamEvent(SERIALCOM, serialMessage, SERIAL_SOURCE);
}

void serialEventRun()
{
    if (SERIALCOM.available())
    {
        serialEvent();
    }
}
#endif
