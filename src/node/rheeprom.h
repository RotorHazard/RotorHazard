#ifndef rheeprom_h
#define rheeprom_h

#include <EEPROM.h>

void eepromWriteWord(int addr, uint16_t val);
uint16_t eepromReadWord(int addr);

#endif
