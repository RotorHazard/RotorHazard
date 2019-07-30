#ifndef eeprom_h
#define eeprom_h

#include <EEPROM.h>

void eepromWriteWord(int addr, uint16_t val);
uint16_t eepromReadWord(int addr);

#endif
