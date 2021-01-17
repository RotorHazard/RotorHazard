#ifndef __TEST__
#include "config.h"
#include "rheeprom.h"

#if !STM32_MODE_FLAG

//Writes 2-byte word to EEPROM at address.
void eepromWriteWord(int addr, uint16_t val)
{
    EEPROM.write(addr, lowByte(val));
    EEPROM.write(addr + 1, highByte(val));
}

//Reads 2-byte word at address from EEPROM.
uint16_t eepromReadWord(int addr)
{
    uint8_t lb = EEPROM.read(addr);
    uint8_t hb = EEPROM.read(addr + 1);
    return (((uint16_t) hb) << (uint16_t)8) + lb;
}

#endif
#endif
