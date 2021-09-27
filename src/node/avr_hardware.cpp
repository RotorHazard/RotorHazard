#include "config.h"
#if TARGET == AVR_TARGET
#include "avr_hardware.h"

AvrHardware defaultHardware;
Hardware& hardware = defaultHardware;

static Message serialMessage;

void serialEvent()
{
    handleStreamEvent(Serial, serialMessage);
}
#endif
