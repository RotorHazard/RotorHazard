#include "../config.h"
#if TARGET == SIL_TARGET
#include "sil_hardware.h"
#include "../commands.h"

SILHardware silHardware;
Hardware& hardware = silHardware;

static Message serialMessage;

void serialEvent() {
    handleStreamEvent(Serial, serialMessage);
}
#endif
