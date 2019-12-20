// RotorHazard FPV Race Timing
// Based on Delta 5 Race Timer by Scott Chin
// SPI driver based on fs_skyrf_58g-main.c Written by Simon Chambers
// I2C functions by Mike Ochtman
//
// MIT License
//
// Copyright (c) 2019 Michael Niggel and other contributors
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

#include <util/atomic.h>
#include <Wire.h>
#include <EEPROM.h>
#include "rhtypes.h"
#include "rssi.h"

// ******************************************************************** //

// *** Node Setup — Set node number here (1–8): ***
#define NODE_NUMBER 0

// Set to 1–8 for manual selection.
// Leave at 0 for automatic selection via hardware pin.
// For automatic selection, ground pins for each node:
//                pin D4 open   pin D4 grounded
// ground pin D5  node 1        node 5
// ground pin D6  node 2        node 6
// ground pin D7  node 3        node 7
// ground pin D8  node 4        node 8

// See https://github.com/RotorHazard/RotorHazard/blob/master/doc/Software%20Setup.md#receiver-nodes-arduinos

// ******************************************************************** //





// i2c address for node
// Node 1 = 8, Node 2 = 10, Node 3 = 12, Node 4 = 14
// Node 5 = 16, Node 6 = 18, Node 7 = 20, Node 8 = 22
static int i2cSlaveAddress = 6 + (NODE_NUMBER * 2);

// API level for read/write commands; increment when commands are modified
#define NODE_API_LEVEL 18

static const int slaveSelectPin = 10;  // Setup data pins for rx5808 comms
static const int spiDataPin = 11;
static const int spiClockPin = 13;

#define MIN_FREQ 100
#define MAX_FREQ 9999

#define READ_ADDRESS 0x00
#define READ_FREQUENCY 0x03
#define READ_LAP_STATS 0x05
#define READ_FILTER_RATIO 0x20    // API_level>=10 uses 16-bit value
#define READ_REVISION_CODE 0x22   // read NODE_API_LEVEL and verification value
#define READ_NODE_RSSI_PEAK 0x23  // read 'state.nodeRssiPeak' value
#define READ_NODE_RSSI_NADIR 0x24  // read 'state.nodeRssiNadir' value
#define READ_ENTER_AT_LEVEL 0x31
#define READ_EXIT_AT_LEVEL 0x32
#define READ_TIME_MILLIS 0x33     // read current 'millis()' value

#define WRITE_FREQUENCY 0x51
#define WRITE_FILTER_RATIO 0x70   // API_level>=10 uses 16-bit value
#define WRITE_ENTER_AT_LEVEL 0x71
#define WRITE_EXIT_AT_LEVEL 0x72

#define MARK_START_TIME 0x77  // mark base time for returned lap-ms-since-start values
#define FORCE_END_CROSSING 0x78  // kill current crossing flag regardless of RSSI value

#define EEPROM_ADRW_RXFREQ 0       //address for stored RX frequency value
#define EEPROM_ADRW_ENTERAT 2      //address for stored 'enterAtLevel'
#define EEPROM_ADRW_EXITAT 4       //address for stored 'exitAtLevel'
#define EEPROM_ADRW_EXPIRE 6       //address for stored catch history expire duration
#define EEPROM_ADRW_CHECKWORD 8    //address for integrity-check value
#define EEPROM_CHECK_VALUE 0x3526  //EEPROM integrity-check value

static uint8_t volatile ioCommand;  // I2C code to identify messages
static uint8_t volatile ioBuffer[32];  // Data array for sending over i2c, up to 32 bytes per message
static int ioBufferSize = 0;
static int ioBufferIndex = 0;

// Defines for fast ADC reads
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))


// Initialize program
void setup()
{
    if (!NODE_NUMBER) {
      pinMode(4, INPUT_PULLUP);
      pinMode(5, INPUT_PULLUP);
      pinMode(6, INPUT_PULLUP);
      pinMode(7, INPUT_PULLUP);
      pinMode(8, INPUT_PULLUP);

      if (digitalRead(4) == HIGH) {
        if (digitalRead(5) == LOW) {
          i2cSlaveAddress = 8;
        }
        else if (digitalRead(6) == LOW) {
          i2cSlaveAddress = 10;
        }
        else if (digitalRead(7) == LOW) {
          i2cSlaveAddress = 12;
        }
        else if (digitalRead(8) == LOW) {
          i2cSlaveAddress = 14;
        }
      } else {
        if (digitalRead(5) == LOW) {
          i2cSlaveAddress = 16;
        }
        else if (digitalRead(6) == LOW) {
          i2cSlaveAddress = 18;
        }
        else if (digitalRead(7) == LOW) {
          i2cSlaveAddress = 20;
        }
        else if (digitalRead(8) == LOW) {
          i2cSlaveAddress = 22;
        }
      }
    }

    Serial.begin(115200);  // Start serial for output/debugging

    pinMode(slaveSelectPin, OUTPUT);  // RX5808 comms
    pinMode(spiDataPin, OUTPUT);
    pinMode(spiClockPin, OUTPUT);
    digitalWrite(slaveSelectPin, HIGH);

    while (!Serial)
    {
    };  // Wait for the Serial port to initialise
    Serial.print(F("Ready: "));
    Serial.println(i2cSlaveAddress);

    Wire.begin(i2cSlaveAddress);  // I2C slave address setup
    Wire.onReceive(i2cReceive);  // Trigger 'i2cReceive' function on incoming data
    Wire.onRequest(i2cTransmit);  // Trigger 'i2cTransmit' function for outgoing data, on master request

    TWAR = (i2cSlaveAddress << 1) | 1;  // enable broadcasts to be received

    // set ADC prescaler to 16 to speedup ADC readings
    sbi(ADCSRA, ADPS2);
    cbi(ADCSRA, ADPS1);
    cbi(ADCSRA, ADPS0);

    // if EEPROM-check value matches then read stored values
    if (readWordFromEeprom(EEPROM_ADRW_CHECKWORD) == EEPROM_CHECK_VALUE)
    {
        settings.vtxFreq = readWordFromEeprom(EEPROM_ADRW_RXFREQ);
        settings.enterAtLevel = readWordFromEeprom(EEPROM_ADRW_ENTERAT);
        settings.exitAtLevel = readWordFromEeprom(EEPROM_ADRW_EXITAT);
    }
    else
    {    // if no match then initialize EEPROM values
        writeWordToEeprom(EEPROM_ADRW_RXFREQ, settings.vtxFreq);
        writeWordToEeprom(EEPROM_ADRW_ENTERAT, settings.enterAtLevel);
        writeWordToEeprom(EEPROM_ADRW_EXITAT, settings.exitAtLevel);
        writeWordToEeprom(EEPROM_ADRW_CHECKWORD, EEPROM_CHECK_VALUE);
    }

    setRxModule(settings.vtxFreq);  // Setup rx module to default frequency

	rssiInit();
}

// Functions for the rx5808 module

void SERIAL_SENDBIT1()
{
    digitalWrite(spiClockPin, LOW);
    delayMicroseconds(300);
    digitalWrite(spiDataPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(spiClockPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(spiClockPin, LOW);
    delayMicroseconds(300);
}

void SERIAL_SENDBIT0()
{
    digitalWrite(spiClockPin, LOW);
    delayMicroseconds(300);
    digitalWrite(spiDataPin, LOW);
    delayMicroseconds(300);
    digitalWrite(spiClockPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(spiClockPin, LOW);
    delayMicroseconds(300);
}

void SERIAL_ENABLE_LOW()
{
    delayMicroseconds(100);
    digitalWrite(slaveSelectPin, LOW);
    delayMicroseconds(100);
}

void SERIAL_ENABLE_HIGH()
{
    delayMicroseconds(100);
    digitalWrite(slaveSelectPin, HIGH);
    delayMicroseconds(100);
}

// Calculate rx5808 register hex value for given frequency in MHz
uint16_t freqMhzToRegVal(uint16_t freqInMhz)
{
    uint16_t tf, N, A;
    tf = (freqInMhz - 479) / 2;
    N = tf / 32;
    A = tf % 32;
    return (N << 7) + A;
}

// Set the frequency given on the rx5808 module
void setRxModule(int frequency)
{
    uint8_t i;  // Used in the for loops

    // Get the hex value to send to the rx module
    uint16_t vtxHex = freqMhzToRegVal(frequency);

    // bit bash out 25 bits of data / Order: A0-3, !R/W, D0-D19 / A0=0, A1=0, A2=0, A3=1, RW=0, D0-19=0
    SERIAL_ENABLE_HIGH();
    delay(2);
    SERIAL_ENABLE_LOW();
    SERIAL_SENDBIT0();
    SERIAL_SENDBIT0();
    SERIAL_SENDBIT0();
    SERIAL_SENDBIT1();
    SERIAL_SENDBIT0();

    for (i = 20; i > 0; i--)
        SERIAL_SENDBIT0();  // Remaining zeros

    SERIAL_ENABLE_HIGH();  // Clock the data in
    delay(2);
    SERIAL_ENABLE_LOW();

    // Second is the channel data from the lookup table, 20 bytes of register data are sent, but the
    // MSB 4 bits are zeros register address = 0x1, write, data0-15=vtxHex data15-19=0x0
    SERIAL_ENABLE_HIGH();
    SERIAL_ENABLE_LOW();

    SERIAL_SENDBIT1();  // Register 0x1
    SERIAL_SENDBIT0();
    SERIAL_SENDBIT0();
    SERIAL_SENDBIT0();

    SERIAL_SENDBIT1();  // Write to register

    // D0-D15, note: loop runs backwards as more efficent on AVR
    for (i = 16; i > 0; i--)
    {
        if (vtxHex & 0x1)
        {  // Is bit high or low?
            SERIAL_SENDBIT1();
        }
        else
        {
            SERIAL_SENDBIT0();
        }
        vtxHex >>= 1;  // Shift bits along to check the next one
    }

    for (i = 4; i > 0; i--)  // Remaining D16-D19
        SERIAL_SENDBIT0();

    SERIAL_ENABLE_HIGH();  // Finished clocking data in
    delay(2);

    digitalWrite(slaveSelectPin, LOW);
    digitalWrite(spiClockPin, LOW);
    digitalWrite(spiDataPin, LOW);
}

// Read the RSSI value for the current channel
rssi_t rssiRead()
{
  // reads 5V value as 0-1023, RX5808 is 3.3V powered so RSSI pin will never output the full range
    int raw = analogRead(0);
    // clamp upper range to fit scaling
    if (raw > 0x01FF)
      raw = 0x01FF;
    // rescale to fit into a byte and remove some jitter
    return raw>>1;
}

#define FREQ_SET        0x01
#define FREQ_CHANGED    0x02
#define ENTERAT_CHANGED 0x04
#define EXITAT_CHANGED  0x08
static uint8_t settingChangedFlags = 0;
static mtime_t loopMillis = 0;

// Main loop
void loop()
{
    mtime_t ms = millis();
    if (ms > loopMillis) {
        loopMillis = ms;
        // read raw RSSI close to taking timestamp
        rssiProcess(rssiRead(), ms);
    }

	/*** update settings ***/

  uint8_t changeFlags;
	ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
		changeFlags = settingChangedFlags;
		settingChangedFlags = 0;
	}
	if (changeFlags & FREQ_SET) {
		uint16_t newVtxFreq;
		ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
			newVtxFreq = settings.vtxFreq;
		}
    setRxModule(newVtxFreq);
    state.rxFreqSetFlag = true;
    Serial.print(F("Set RX freq = "));
    Serial.println(newVtxFreq);

		if (changeFlags & FREQ_CHANGED) {
			writeWordToEeprom(EEPROM_ADRW_RXFREQ, newVtxFreq);
			rssiStateReset();  // restart rssi peak tracking for node
			Serial.println(F("Set nodeRssiPeak = 0, nodeRssiNadir = Max"));
		}
	}

	if (changeFlags & ENTERAT_CHANGED) {
    writeWordToEeprom(EEPROM_ADRW_ENTERAT, settings.enterAtLevel);
	}

	if (changeFlags & EXITAT_CHANGED) {
    writeWordToEeprom(EEPROM_ADRW_EXITAT, settings.exitAtLevel);
	}
}


// Function called by twi interrupt service when master sends information to the slave
// or when master sets up a specific read request
void i2cReceive(int byteCount)
{  // Number of bytes in rx buffer
   // If byteCount is zero, the master only checked for presence of the slave device, no response necessary
    if (byteCount == 0)
    {
        Serial.println(F("Error: no bytes for a receive?"));
        return;
    }

    if (byteCount != Wire.available())
    {
        Serial.println(F("Error: rx byte count and wire available don't agree"));
    }

    ioCommand = Wire.read();  // The first byte sent is a command byte

    if (ioCommand > 0x50)
    {  // Commands > 0x50 are writes TO this slave
        i2cHandleRx(ioCommand);
    }
    else
    {  // Otherwise this is a request FROM this device
        if (Wire.available())
        {  // There shouldn't be any data present on the line for a read request
            Serial.print(F("Error: Wire.available() on a read request."));
            Serial.println(ioCommand, HEX);
            while (Wire.available())
            {
                Wire.read();
            }
        }
    }
}

bool readAndValidateIoBuffer(byte command, int expectedSize)
{
    uint8_t checksum = 0;
    ioBufferSize = 0;
    ioBufferIndex = 0;

    if (expectedSize == 0)
    {
        Serial.println(F("No Expected Size"));
        return true;
    }

    if (!Wire.available())
    {
        Serial.println(F("Nothing Avialable"));
        return false;
    }

    while (Wire.available())
    {
        ioBuffer[ioBufferSize++] = Wire.read();
        if (expectedSize + 1 < ioBufferSize)
        {
            checksum += ioBuffer[ioBufferSize - 1];
        }
    }

    if (checksum != ioBuffer[ioBufferSize - 1]
            || ioBufferSize - 2 != expectedSize)
    {
        Serial.println(F("invalid checksum"));
        Serial.println(checksum);
        Serial.println(ioBuffer[ioBufferSize - 1]);
        Serial.println(ioBufferSize - 2);
        Serial.println(expectedSize);
        return false;
    }

    if (command != ioBuffer[ioBufferSize - 2])
    {
        Serial.println(F("command does not match"));
        return false;
    }
    return true;
}

uint8_t ioBufferRead8()
{
    return ioBuffer[ioBufferIndex++];
}

uint16_t ioBufferRead16()
{
    uint16_t result;
    result = ioBuffer[ioBufferIndex++];
    result = (result << 8) | ioBuffer[ioBufferIndex++];
    return result;
}

uint32_t ioBufferRead32()
{
    uint32_t result;
    result = ioBuffer[ioBufferIndex++];
    result = (result << 8) | ioBuffer[ioBufferIndex++];
    result = (result << 8) | ioBuffer[ioBufferIndex++];
    result = (result << 8) | ioBuffer[ioBufferIndex++];
    return result;
}

void ioBufferWrite8(uint8_t data)
{
    ioBuffer[ioBufferSize++] = data;
}

void ioBufferWrite16(uint16_t data)
{
    ioBuffer[ioBufferSize++] = (uint16_t)(data >> 8);
    ioBuffer[ioBufferSize++] = (uint16_t)(data & 0xFF);
}

void ioBufferWrite32(uint32_t data)
{
    ioBuffer[ioBufferSize++] = (uint32_t)(data >> 24);
    ioBuffer[ioBufferSize++] = (uint32_t)(data >> 16);
    ioBuffer[ioBufferSize++] = (uint32_t)(data >> 8);
    ioBuffer[ioBufferSize++] = (uint32_t)(data & 0xFF);
}

void ioBufferWriteChecksum()
{
    uint8_t checksum = 0;
    for (int i = 0; i < ioBufferSize; i++)
    {
        checksum += ioBuffer[i];
    }

    ioBufferWrite8(checksum);
}

#define ioBufferReadRssi() (ioBufferRead8())
#define ioBufferWriteRssi(rssi) (ioBufferWrite8(rssi))

// Function called by i2cReceive for writes TO this device, the I2C Master has sent data
// using one of the SMBus write commands, if the MSB of 'command' is 0, master is sending only
// Returns the number of bytes read, or FF if unrecognised command or mismatch between
// data expected and received
byte i2cHandleRx(byte command)
{  // The first byte sent by the I2C master is the command
    bool success = false;
    uint16_t u16val;
    rssi_t rssiVal;

    switch (command)
    {
        case WRITE_FREQUENCY:
            if (readAndValidateIoBuffer(0x51, 2))
            {
                u16val = ioBufferRead16();
                if (u16val >= MIN_FREQ && u16val <= MAX_FREQ) {
	                if (u16val != settings.vtxFreq) {
		                settings.vtxFreq = u16val;
	                    settingChangedFlags |= FREQ_CHANGED;
	                }
	                settingChangedFlags |= FREQ_SET;
	                success = true;
                }
            }
            break;

        case WRITE_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            if (readAndValidateIoBuffer(WRITE_ENTER_AT_LEVEL, 1))
            {
                rssiVal = ioBufferReadRssi();
                if (rssiVal != settings.enterAtLevel) {
	            	settings.enterAtLevel = rssiVal;
	                settingChangedFlags |= ENTERAT_CHANGED;
                }
                success = true;
            }
            break;

        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            if (readAndValidateIoBuffer(WRITE_EXIT_AT_LEVEL, 1))
            {
                rssiVal = ioBufferReadRssi();
                if (rssiVal != settings.exitAtLevel) {
	            	settings.exitAtLevel = rssiVal;
	                settingChangedFlags |= EXITAT_CHANGED;
                }
                success = true;
            }
            break;

        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
            rssiEndCrossing();

            if (readAndValidateIoBuffer(FORCE_END_CROSSING, 1))  // read byte value (not used)
                success = true;
            break;

    }

    ioCommand = 0;  // Clear previous command

    if (!success)
    {  // Set control to rxFault if 0xFF result
        Serial.print(F("RX Fault command: "));
        Serial.println(command, HEX);
    }
    return success;
}

// Function called by twi interrupt service when the Master wants to get data from the Slave
// No parameters and no returns
// A transmit buffer (ioBuffer) is populated with the data before sending.
void i2cTransmit()
{
    ioBufferSize = 0;

    switch (ioCommand)
    {
        case READ_ADDRESS:
            ioBufferWrite8(i2cSlaveAddress);
            break;

        case READ_FREQUENCY:
            ioBufferWrite16(settings.vtxFreq);
            break;

        case READ_LAP_STATS:
            {
              mtime_t now = millis();
              ioBufferWrite8(lastPass.lap);
              ioBufferWrite16(uint16_t(now - lastPass.timestamp));  // ms since lap
              ioBufferWriteRssi(state.rssi);
              ioBufferWriteRssi(state.nodeRssiPeak);
              ioBufferWriteRssi(lastPass.rssiPeak);  // RSSI peak for last lap pass
              ioBufferWrite16(uint16_t(state.loopTimeMicros));
              ioBufferWrite8(state.crossing ? (uint8_t) 1 : (uint8_t) 0);  // 'crossing' status
              ioBufferWriteRssi(lastPass.rssiNadir);  // lowest rssi since end of last pass
              ioBufferWriteRssi(state.nodeRssiNadir);

              if (isPeakValid(history.peakSendRssi)) {
                  // send peak and reset
                  ioBufferWriteRssi(history.peakSendRssi);
                  ioBufferWrite16(uint16_t(now - history.peakSendFirstTime));
                  ioBufferWrite16(uint16_t(now - history.peakSendLastTime));
                  history.peakSendRssi = 0;
              } else {
                  ioBufferWriteRssi(0);
                  ioBufferWrite16(0);
                  ioBufferWrite16(0);
              }

              if (isNadirValid(history.nadirSendRssi)) {
                  // send nadir and reset
                  ioBufferWriteRssi(history.nadirSendRssi);
                  ioBufferWrite16(uint16_t(now - history.nadirSendTime));
                  history.nadirSendRssi = MAX_RSSI;
              } else {
                  ioBufferWriteRssi(0);
                  ioBufferWrite16(0);
              }
            }
            break;

        case READ_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            ioBufferWriteRssi(settings.enterAtLevel);
            break;

        case READ_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            ioBufferWriteRssi(settings.exitAtLevel);
            break;

        case READ_REVISION_CODE:  // reply with NODE_API_LEVEL and verification value
            ioBufferWrite16((0x25 << 8) + NODE_API_LEVEL);
            break;

        case READ_NODE_RSSI_PEAK:
            ioBufferWriteRssi(state.nodeRssiPeak);
            break;

        case READ_NODE_RSSI_NADIR:
            ioBufferWriteRssi(state.nodeRssiNadir);
            break;

        case READ_TIME_MILLIS:
            ioBufferWrite32(millis());
            break;

        default:  // If an invalid command is sent, write nothing back, master must react
            Serial.print(F("TX Fault command: "));
            Serial.println(ioCommand, HEX);
    }

    ioCommand = 0;  // Clear previous command

    if (ioBufferSize > 0)
    {  // If there is pending data, send it
        ioBufferWriteChecksum();
        Wire.write((byte *) &ioBuffer, ioBufferSize);
    }
}

//Writes 2-byte word to EEPROM at address.
void writeWordToEeprom(int addr, uint16_t val)
{
    EEPROM.write(addr, lowByte(val));
    EEPROM.write(addr + 1, highByte(val));
}

//Reads 2-byte word at address from EEPROM.
uint16_t readWordFromEeprom(int addr)
{
    const uint8_t lb = EEPROM.read(addr);
    const uint8_t hb = EEPROM.read(addr + 1);
    return (((uint16_t) hb) << 8) + lb;
}
