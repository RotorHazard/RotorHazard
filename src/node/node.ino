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

#include <Wire.h>
#include <EEPROM.h>
#include "FastRunningMedian.h"

// ******************************************************************** //

// *** Node Setup — Set node number here (1–8): ***
#define NODE_NUMBER 0

// Set to 1–8 for manual selection.
// Leave at 0 for automatic selection via hardware pin.
// For automatic selection, ground pins for each node:
//                pin 4 open    pin 4 grounded
// ground pin 5   node 1        node 5
// ground pin 6   node 2        node 6
// ground pin 7   node 3        node 7
// ground pin 8   node 4        node 8

// See https://github.com/RotorHazard/RotorHazard/blob/master/doc/Software%20Setup.md#receiver-nodes-arduinos

// ******************************************************************** //





// i2c address for node
// Node 1 = 8, Node 2 = 10, Node 3 = 12, Node 4 = 14
// Node 5 = 16, Node 6 = 18, Node 7 = 20, Node 8 = 22
int i2cSlaveAddress (6 + (NODE_NUMBER * 2));

// API level for read/write commands; increment when commands are modified
#define NODE_API_LEVEL 18 //RF was 17, now 18

const int slaveSelectPin = 10;  // Setup data pins for rx5808 comms
const int spiDataPin = 11;
const int spiClockPin = 13;
const int voltageInputPin = 1; //RF voltage input

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
#define READ_CATCH_HISTORY 0x34
#define READ_HISTORY_EXPIRE_DURATION 0x35
#define READ_NODE_SYNC 0x36       // check node sync value
#define READ_CLOCK_ERROR 0x37
#define READ_VOLTAGE 0x38 //RF read node voltage

#define WRITE_FREQUENCY 0x51
#define WRITE_FILTER_RATIO 0x70   // API_level>=10 uses 16-bit value
#define WRITE_ENTER_AT_LEVEL 0x71
#define WRITE_EXIT_AT_LEVEL 0x72
#define WRITE_HISTORY_EXPIRE_DURATION 0x73  // adjust history catch window size
#define WRITE_NODE_SYNC 0x74   // set node sync value
#define WRITE_CLOCK_ERROR 0x75   // set pi clock differential

#define MARK_START_TIME 0x77  // mark base time for returned lap-ms-since-start values
#define FORCE_END_CROSSING 0x78  // kill current crossing flag regardless of RSSI value

#define FILTER_RATIO_DIVIDER 10000.0f

#define EEPROM_ADRW_RXFREQ 0       //address for stored RX frequency value
#define EEPROM_ADRW_ENTERAT 2      //address for stored 'enterAtLevel'
#define EEPROM_ADRW_EXITAT 4       //address for stored 'exitAtLevel'
#define EEPROM_ADRW_EXPIRE 6       //address for stored catch history expire duration
#define EEPROM_ADRW_CHECKWORD 8    //address for integrity-check value
#define EEPROM_CHECK_VALUE 0x3526  //EEPROM integrity-check value

struct
{
    uint16_t volatile vtxFreq = 5800;
    // lap pass begins when RSSI is at or above this level
    uint16_t volatile enterAtLevel = 192;
    // lap pass ends when RSSI goes below this level
    uint16_t volatile exitAtLevel = 160;
} settings;

struct
{
    bool volatile crossing = false; // True when the quad is going through the gate
    uint16_t volatile rssiSmoothed = 0; // Smoothed rssi value
    uint16_t volatile lastRssiSmoothed = 0;
    uint32_t volatile rssiTimestamp = 0; // timestamp of the smoothed value

    uint16_t volatile passRssiPeakRaw = 0; // peak raw rssi seen during current pass
    uint16_t volatile passRssiPeak = 0; // peak smoothed rssi seen during current pass
    uint32_t volatile passRssiPeakRawTime = 0; // time of the first peak raw rssi for the current pass
    uint32_t volatile passRssiPeakRawLastTime = 0; // time of the last peak raw rssi for the current pass
    uint16_t volatile passRssiNadir = 999; // lowest smoothed rssi seen since end of last pass

    uint16_t volatile nodeRssiPeak = 0; // peak smoothed rssi seen since the node frequency was set
    uint16_t volatile nodeRssiNadir = 999; // lowest smoothed rssi seen since the node frequency was set

    bool volatile rxFreqSetFlag = false; // Set true after initial WRITE_FREQUENCY command received

    // variables to track the loop time
    uint32_t volatile loopTime = 0;
    uint32_t volatile lastloopMicros = 0;
} state;

struct
{
    uint16_t volatile peakRssi;
    uint32_t volatile peakFirstTime;
    uint32_t volatile peakLastTime;
    uint32_t volatile peakTime;
    bool volatile peakSend;

    uint16_t volatile nadirRssi;
    uint16_t volatile nadirTime;
    bool volatile nadirSend;
    
    bool volatile isRising;
    bool volatile isFalling;
} history;

struct
{
    uint16_t volatile rssiPeakRaw;
    uint16_t volatile rssiPeak;
    uint32_t volatile timeStamp;
    uint16_t volatile rssiNadir;
    uint8_t volatile lap;
} lastPass;

uint8_t volatile ioCommand;  // I2C code to identify messages
uint8_t volatile ioBuffer[32];  // Data array for sending over i2c, up to 32 bytes per message
int ioBufferSize = 0;
int ioBufferIndex = 0;

// Defines for fast ADC reads
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))


#define SmoothingSamples 193
FastRunningMedian<uint16_t, SmoothingSamples, 0> rssiMedian;

#define SmoothingTimestampSize 97 // half median window, rounded up
uint32_t volatile SmoothingTimestamps[SmoothingTimestampSize];
uint8_t SmoothingTimestampsIndex = 0;

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

    // Initialize defaults
    lastPass.rssiPeakRaw = 0;
    lastPass.rssiPeak = 0;
    lastPass.lap = 0;
    lastPass.timeStamp = 0;

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
int rssiRead()
{
    return analogRead(0);
}

//RF: Read the voltage of the node battery voltage divider on A1
int voltageRead()
{
  return analogRead(1);
}

uint32_t loopMillis = 0;
uint16_t lastRssi = 0;

// Main loop
void loop()
{
    state.lastRssiSmoothed = state.rssiSmoothed;
    
    uint32_t loopMicros = micros();
    loopMillis = millis();
    
    // read raw RSSI close to taking timestamp
    rssiMedian.addValue(rssiRead());
    state.rssiSmoothed = rssiMedian.getMedian(); // retrieve the median

    SmoothingTimestamps[SmoothingTimestampsIndex] = loopMillis;
    SmoothingTimestampsIndex++;
    if (SmoothingTimestampsIndex >= SmoothingTimestampSize) {
        SmoothingTimestampsIndex = 0;
    }
    state.rssiTimestamp = SmoothingTimestamps[SmoothingTimestampsIndex];

    if (state.rxFreqSetFlag)
    {  //don't start operations until after first WRITE_FREQUENCY command is received

        // update history
        if (state.rssiSmoothed > state.lastRssiSmoothed) { // RSSI is rising
          if (history.peakSend = true) {
            if (state.rssiSmoothed > history.peakRssi) {
              history.peakSend = false;
            }
          }
        
          if (!history.peakSend) {
            if (state.rssiSmoothed > history.peakRssi) {
              history.peakRssi = state.rssiSmoothed;
              history.peakFirstTime = history.peakLastTime = state.rssiTimestamp;
            }
          }
        
          if (history.isFalling) {
            history.nadirTime = state.rssiTimestamp;
            history.nadirSend = true;
          }
        
          history.isRising = true;
          history.isFalling = false;
        
        } else if (state.rssiSmoothed < state.lastRssiSmoothed) { // RSSI is falling
          if (history.isRising) {
            history.peakTime = (history.peakFirstTime + history.peakLastTime) / 2;
            history.peakSend = true;
          }
        
          if (history.nadirSend) {
            if (state.rssiSmoothed < history.nadirRssi) {
              history.nadirSend = false;
            }
          }
        
          if (!history.nadirSend) {
            history.nadirRssi = state.rssiSmoothed;
          }
        
          history.isRising = false;
          history.isFalling = true;
          
        } else { // RSSI is equal
          if (history.isRising) {
            history.peakLastTime = state.rssiTimestamp;
          }
        }

        // Keep track of peak (smoothed) rssi
        if (state.rssiSmoothed > state.nodeRssiPeak)
        {
            state.nodeRssiPeak = state.rssiSmoothed;
            Serial.print(F("New nodeRssiPeak = "));
            Serial.println(state.nodeRssiPeak);
        }

        if (state.rssiSmoothed < state.nodeRssiNadir)
        {
            state.nodeRssiNadir = state.rssiSmoothed;
            Serial.print(F("New nodeRssiNadir = "));
            Serial.println(state.nodeRssiNadir);
        }

        if ((!state.crossing) && state.rssiSmoothed >= settings.enterAtLevel)
        {
            state.crossing = true;  // quad is going through the gate (lap pass starting)
            Serial.println(F("Crossing = True"));
        }

        // Find the peak rssi and the time it occured during a crossing event
        if (state.rssiSmoothed >= state.passRssiPeakRaw)
        {
            // if at max peak for more than one iteration then track first
            //  and last timestamp so middle-timestamp value can be returned
            state.passRssiPeakRawLastTime = state.rssiTimestamp;

            if (state.rssiSmoothed > state.passRssiPeakRaw)
            {
                // this is first time this peak-raw-RSSI value was seen, so save value and timestamp
                state.passRssiPeakRaw = state.rssiSmoothed;
                state.passRssiPeakRawTime = state.passRssiPeakRawLastTime;
            }
        }

        // track lowest smoothed rssi seen since end of last pass
        if (state.rssiSmoothed < state.passRssiNadir)
            state.passRssiNadir = state.rssiSmoothed;

        if (state.crossing)
        {  //lap pass is in progress

            // track RSSI peak for current lap pass
            if (state.rssiSmoothed > state.passRssiPeak)
                state.passRssiPeak = state.rssiSmoothed;

            // see if quad has left the gate
            if (state.rssiSmoothed < settings.exitAtLevel)
            {
                Serial.println(F("Crossing = False"));
                end_crossing();
            }
        }
    }

    // Calculate the time it takes to run the main loop
    state.loopTime = loopMicros - state.lastloopMicros;
    state.lastloopMicros = loopMicros;

    // Status LED
    if (state.crossing ||  // on while crossing
        (loopMillis / 100) % 10 == 0 // blink
      ) {
      digitalWrite(LED_BUILTIN, HIGH);
    } else {
      digitalWrite(LED_BUILTIN, LOW);
    }

}

// Function called when crossing ends (by RSSI or I2C command)
void end_crossing() {
    // save values for lap pass
    lastPass.rssiPeakRaw = state.passRssiPeakRaw;
    lastPass.rssiPeak = state.passRssiPeak;
    // lap timestamp is between first and last peak RSSI
    lastPass.timeStamp = (state.passRssiPeakRawLastTime + state.passRssiPeakRawTime) / 2;
    lastPass.rssiNadir = state.passRssiNadir;
    lastPass.lap = lastPass.lap + 1;

    // reset lap-pass variables
    state.crossing = false;
    state.passRssiPeakRaw = 0;
    state.passRssiPeak = 0;
    state.passRssiNadir = 999;
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

// Function called by i2cReceive for writes TO this device, the I2C Master has sent data
// using one of the SMBus write commands, if the MSB of 'command' is 0, master is sending only
// Returns the number of bytes read, or FF if unrecognised command or mismatch between
// data expected and received
byte i2cHandleRx(byte command)
{  // The first byte sent by the I2C master is the command
    bool success = false;
    uint16_t u16val;

    switch (command)
    {
        case WRITE_FREQUENCY:
            if (readAndValidateIoBuffer(0x51, 2))
            {
                u16val = settings.vtxFreq;
                settings.vtxFreq = ioBufferRead16();
                setRxModule(settings.vtxFreq);  // Shouldn't do this in Interrupt Service Routine
                success = true;
                state.rxFreqSetFlag = true;
                Serial.print(F("Set RX freq = "));
                Serial.println(settings.vtxFreq);
                if (settings.vtxFreq != u16val)
                {  // if RX frequency changed
                    writeWordToEeprom(EEPROM_ADRW_RXFREQ, settings.vtxFreq);
                    state.nodeRssiPeak = 0;  // restart rssi peak tracking for node
                    state.nodeRssiNadir = 999;
                    Serial.println(F("Set nodeRssiPeak = 0, nodeRssiNadir = 999"));
                }
            }
            break;

        case WRITE_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            if (readAndValidateIoBuffer(WRITE_ENTER_AT_LEVEL, 2))
            {
                settings.enterAtLevel = ioBufferRead16();
                writeWordToEeprom(EEPROM_ADRW_ENTERAT, settings.enterAtLevel);
                success = true;
            }
            break;

        case WRITE_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            if (readAndValidateIoBuffer(WRITE_EXIT_AT_LEVEL, 2))
            {
                settings.exitAtLevel = ioBufferRead16();
                writeWordToEeprom(EEPROM_ADRW_EXITAT, settings.exitAtLevel);
                success = true;
            }
            break;

        case FORCE_END_CROSSING:  // kill current crossing flag regardless of RSSI value
            end_crossing();

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
            ioBufferWrite8(lastPass.lap);
            ioBufferWrite32(millis() - lastPass.timeStamp);  // ms since lap
            ioBufferWrite16(state.rssiSmoothed);
            ioBufferWrite16(state.nodeRssiPeak);
            ioBufferWrite16(lastPass.rssiPeak);  // RSSI peak for last lap pass
            ioBufferWrite32(state.loopTime);
            ioBufferWrite8(state.crossing ? (uint8_t) 1 : (uint8_t) 0);  // 'crossing' status
            ioBufferWrite16(lastPass.rssiNadir);  // lowest rssi since end of last pass
            ioBufferWrite16(state.nodeRssiNadir);

            if (history.peakSend) {
                ioBufferWrite16(history.peakRssi);
                ioBufferWrite16(uint16_t(millis() - history.peakTime));
                history.peakSend = false;
                history.peakRssi = state.rssiSmoothed;
            } else {
                ioBufferWrite16(0);
                ioBufferWrite16(0);
            }
            
            if (history.nadirSend) {
                ioBufferWrite16(history.nadirRssi);
                ioBufferWrite16(uint16_t(millis() - history.nadirTime));
                history.nadirSend = false;
                history.nadirRssi = state.rssiSmoothed;
            } else {
                ioBufferWrite16(0);
                ioBufferWrite16(0);
            }
            break;

        case READ_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            ioBufferWrite16(settings.enterAtLevel);
            break;

        case READ_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            ioBufferWrite16(settings.exitAtLevel);
            break;

        case READ_REVISION_CODE:  // reply with NODE_API_LEVEL and verification value
            ioBufferWrite16((0x25 << 8) + NODE_API_LEVEL);
            break;

        case READ_NODE_RSSI_PEAK:
            ioBufferWrite16(state.nodeRssiPeak);
            break;

        case READ_NODE_RSSI_NADIR:
            ioBufferWrite16(state.nodeRssiNadir);
            break;

        case READ_TIME_MILLIS:
            ioBufferWrite32(millis());
            break;

        case READ_VOLTAGE: // RF: READ_VOLTAGE will get the current node voltage from the defined analog pin
            ioBufferWrite16(voltageRead()); 
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
