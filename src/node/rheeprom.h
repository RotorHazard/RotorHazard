#ifndef rheeprom_h
#define rheeprom_h

#include "config.h"

#if !STM32_MODE_FLAG

#include <EEPROM.h>

void eepromWriteWord(int addr, uint16_t val);
uint16_t eepromReadWord(int addr);

#endif
#endif
