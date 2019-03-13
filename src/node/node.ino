// RotorHazard FPV Race Timing
// Based on Delta 5 Race Timer by Scott Chin
// SPI driver based on fs_skyrf_58g-main.c Written by Simon Chambers
// I2C functions by Mike Ochtman
//
// MIT License
//
// Copyright (c) 2017 Scott G Chin
// Copyright (c) 2019 Michael Niggel and Eric Thomas
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


// ******************************************************************** //

// *** Node Setup — Set node number here (1–8): ***
#define NODE_NUMBER 0

// Set to 1–8 for manual selection.
// Or, set to 0 for automatic selection via hardware pin.
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
#define NODE_API_LEVEL 15

const int slaveSelectPin = 10;  // Setup data pins for rx5808 comms
const int spiDataPin = 11;
const int spiClockPin = 13;

#define READ_ADDRESS 0x00
#define READ_FREQUENCY 0x03
#define READ_LAP_STATS 0x05
#define READ_FILTER_RATIO 0x20    // API_level>=10 uses 16-bit value
#define READ_REVISION_CODE 0x22   // read NODE_API_LEVEL and verification value
#define READ_NODE_RSSI_PEAK 0x23  // read 'state.nodeRssiPeak' value
#define READ_NODE_RSSI_NADIR 0x24  // read 'state.nodeRssiNadir' value
#define READ_ENTER_AT_LEVEL 0x31
#define READ_EXIT_AT_LEVEL 0x32
#define READ_HISTORY_EXPIRE_DURATION 0x35
#define READ_TIME_MILLIS 0x33     // read current 'millis()' value
#define READ_CATCH_HISTORY 0x34

#define WRITE_FREQUENCY 0x51
#define WRITE_FILTER_RATIO 0x70   // API_level>=10 uses 16-bit value
#define WRITE_ENTER_AT_LEVEL 0x71
#define WRITE_EXIT_AT_LEVEL 0x72
#define WRITE_HISTORY_EXPIRE_DURATION 0x73  // adjust history catch window size
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
    uint16_t volatile filterRatio = 10;
    float volatile filterRatioFloat = 0.0f;
} settings;

struct
{
    // True when the quad is going through the gate
    bool volatile crossing = false;
    // Current unsmoothed rssi
    uint16_t volatile rssiRaw = 0;
    // Smoothed rssi value, needs to be a float for smoothing to work
    float volatile rssiSmoothed = 0;
    // int representation of the smoothed rssi value
    uint16_t volatile rssi = 0;
    // peak raw rssi seen during current pass
    uint16_t volatile passRssiPeakRaw = 0;
    // peak smoothed rssi seen during current pass
    uint16_t volatile passRssiPeak = 0;
    // time of the first peak raw rssi for the current pass
    uint32_t volatile passRssiPeakRawTime = 0;
    // time of the last peak raw rssi for the current pass
    uint32_t volatile passRssiPeakRawLastTime = 0;
    // lowest smoothed rssi seen since end of last pass
    uint16_t volatile passRssiNadir = 999;
    // peak smoothed rssi seen since the node frequency was set
    uint16_t volatile nodeRssiPeak = 0;
    // lowest smoothed rssi seen since the node frequency was set
    uint16_t volatile nodeRssiNadir = 999;
    // Set true after initial WRITE_FREQUENCY command received
    bool volatile rxFreqSetFlag = false;
    // base time for returned lap-ms-since-start values
    uint32_t volatile raceStartTimeStamp = 0;

    // variables to track the loop time
    uint32_t volatile loopTime = 0;
    uint32_t volatile lastLoopTimeStamp = 0;
} state;

struct
{
    uint16_t volatile rssiPeakRaw;
    uint16_t volatile rssiPeak;
    uint32_t volatile timeStamp;
    uint16_t volatile rssiNadir;
    uint8_t volatile lap;
} lastPass;

struct
{
    // catch window in milliseconds
    uint32_t expireDuration = 10000; // default is 10 seconds

    // minimum smoothed rssi
    uint16_t volatile rssiMin;
    // when to look for a new minimum
    uint32_t volatile minExpires;

    // maximum smoothed rssi
    uint16_t volatile rssiMax;
    // peak RSSI
    uint16_t volatile rssiPeak;
    // first peak timestamp
    uint32_t volatile peakFirstTime;
    // last peak timestamp
    uint32_t volatile peakLastTime;
    // when to look for a new maximum
    uint32_t volatile maxExpires;
} history;

uint8_t volatile ioCommand;  // I2C code to identify messages
uint8_t volatile ioBuffer[32];  // Data array for sending over i2c, up to 32 bytes per message
int ioBufferSize = 0;
int ioBufferIndex = 0;

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
    Serial.print("Ready: ");
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
    settings.filterRatioFloat = settings.filterRatio / FILTER_RATIO_DIVIDER;
    state.rssi = 0;
    lastPass.rssiPeakRaw = 0;
    lastPass.rssiPeak = 0;
    lastPass.lap = 0;
    lastPass.timeStamp = 0;

    history.rssiMin = 999;
    history.minExpires = 0;
    history.rssiMax = 0;
    history.rssiPeak = 0;
    history.peakFirstTime = 0;
    history.peakLastTime = 0;
    history.maxExpires = 0;

    // if EEPROM-check value matches then read stored values
    if (readWordFromEeprom(EEPROM_ADRW_CHECKWORD) == EEPROM_CHECK_VALUE)
    {
        settings.vtxFreq = readWordFromEeprom(EEPROM_ADRW_RXFREQ);
        settings.enterAtLevel = readWordFromEeprom(EEPROM_ADRW_ENTERAT);
        settings.exitAtLevel = readWordFromEeprom(EEPROM_ADRW_EXITAT);
        history.expireDuration = readWordFromEeprom(EEPROM_ADRW_EXPIRE);
    }
    else
    {    // if no match then initialize EEPROM values
        writeWordToEeprom(EEPROM_ADRW_RXFREQ, settings.vtxFreq);
        writeWordToEeprom(EEPROM_ADRW_ENTERAT, settings.enterAtLevel);
        writeWordToEeprom(EEPROM_ADRW_EXITAT, settings.exitAtLevel);
        writeWordToEeprom(EEPROM_ADRW_EXPIRE, history.expireDuration);
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

// Main loop
void loop()
{
    //delay(250);
    uint32_t loopMicros = micros();
    uint32_t loopMillis = millis();

    // Calculate the time it takes to run the main loop
    uint32_t lastLoopTimeStamp = state.lastLoopTimeStamp;
    state.lastLoopTimeStamp = loopMicros;
    state.loopTime = state.lastLoopTimeStamp - lastLoopTimeStamp;

    state.rssiRaw = rssiRead();
    state.rssiSmoothed = (settings.filterRatioFloat * (float) state.rssiRaw)
            + ((1.0f - settings.filterRatioFloat) * state.rssiSmoothed);
    state.rssi = (int) state.rssiSmoothed;

    if (state.rxFreqSetFlag)
    {  //don't start operations until after first WRITE_FREQUENCY command is received

        // Keep track of peak (smoothed) rssi
        if (state.rssi > state.nodeRssiPeak)
        {
            state.nodeRssiPeak = state.rssi;
            Serial.print("New nodeRssiPeak = ");
            Serial.println(state.nodeRssiPeak);
        }

        if (state.rssi < state.nodeRssiNadir)
        {
            state.nodeRssiNadir = state.rssi;
            Serial.print("New nodeRssiNadir = ");
            Serial.println(state.nodeRssiNadir);
        }

        if ((!state.crossing) && state.rssi >= settings.enterAtLevel)
        {
            state.crossing = true;  // quad is going through the gate (lap pass starting)
            Serial.println("Crossing = True");
        }

        // Find the peak rssi and the time it occured during a crossing event
        // Use the raw value to account for the delay in smoothing.
        if (state.rssiRaw >= state.passRssiPeakRaw)
        {
            // if at max peak for more than one iteration then track first
            //  and last timestamp so middle-timestamp value can be returned
            state.passRssiPeakRawLastTime = loopMillis;

            if (state.rssiRaw > state.passRssiPeakRaw)
            {
                // this is first time this peak-raw-RSSI value was seen, so save value and timestamp
                state.passRssiPeakRaw = state.rssiRaw;
                state.passRssiPeakRawTime = state.passRssiPeakRawLastTime;
            }
        }

        // track lowest smoothed rssi seen since end of last pass
        if (state.rssi < state.passRssiNadir)
            state.passRssiNadir = state.rssi;

        if (state.crossing)
        {  //lap pass is in progress

            // track RSSI peak for current lap pass
            if (state.rssi > state.passRssiPeak)
                state.passRssiPeak = state.rssi;

            // see if quad has left the gate
            if (state.rssi < settings.exitAtLevel)
            {
                Serial.println("Crossing = False");
                end_crossing();
            }
        }

        // Manual pass catching logic

        // if catch history expires, reset all values (including peak check)
        if (loopMillis > history.maxExpires) {
            // use smoothed RSSI for determining expiration
            history.rssiMax = state.rssiSmoothed;
            history.maxExpires = loopMillis + history.expireDuration;

            // read raw RSSI to get accurate pass time
            history.rssiPeak = state.rssiRaw;
            history.peakFirstTime = loopMillis;
            history.peakLastTime = loopMillis;
        }

        // if a new peak is found, reset exipration (track peak for at least this long)
        if (state.rssiSmoothed > history.rssiMax) {
            history.rssiMax = state.rssiSmoothed;
            history.maxExpires = loopMillis + history.expireDuration;
        }

        if (state.rssiRaw == history.rssiPeak) {
            history.peakLastTime = loopMillis;
        } else if (state.rssiRaw > history.rssiPeak) {
            history.rssiPeak = state.rssiRaw;
            history.peakFirstTime = loopMillis;
            history.peakLastTime = loopMillis;
        }

        // if no lower values read within catch history, reset all values
        // if a lower value is read, reset exipration (track low value for at least this long)
        if (state.rssiSmoothed < history.rssiMin
            || loopMillis > history.minExpires) {
            history.rssiMin = state.rssiSmoothed;
            history.minExpires = loopMillis + history.expireDuration;
        }

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
        Serial.println("Error: no bytes for a receive?");
        return;
    }

    if (byteCount != Wire.available())
    {
        Serial.println("Error: rx byte count and wire available don't agree");
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
            Serial.print("Error: Wire.available() on a read request.");
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
        Serial.println("No Expected Size");
        return true;
    }

    if (!Wire.available())
    {
        Serial.println("Nothing Avialable");
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
        Serial.println("invalid checksum");
        Serial.println(checksum);
        Serial.println(ioBuffer[ioBufferSize - 1]);
        Serial.println(ioBufferSize - 2);
        Serial.println(expectedSize);
        return false;
    }

    if (command != ioBuffer[ioBufferSize - 2])
    {
        Serial.println("command does not match");
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
    ioBuffer[ioBufferSize++] = (uint16_t)(data >> 24);
    ioBuffer[ioBufferSize++] = (uint16_t)(data >> 16);
    ioBuffer[ioBufferSize++] = (uint16_t)(data >> 8);
    ioBuffer[ioBufferSize++] = (uint16_t)(data & 0xFF);
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
                Serial.print("Set RX freq = ");
                Serial.println(settings.vtxFreq);
                if (settings.vtxFreq != u16val)
                {  // if RX frequency changed
                    writeWordToEeprom(EEPROM_ADRW_RXFREQ, settings.vtxFreq);
                    state.nodeRssiPeak = 0;  // restart rssi peak tracking for node
                    state.nodeRssiNadir = 999;
                    Serial.println("Set nodeRssiPeak = 0, nodeRssiNadir = 999");
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

        case WRITE_FILTER_RATIO:
            if (readAndValidateIoBuffer(WRITE_FILTER_RATIO, 2))
            {
                u16val = ioBufferRead16();
                if (u16val >= 1 && u16val <= FILTER_RATIO_DIVIDER)
                {
                    settings.filterRatio = u16val;
                    settings.filterRatioFloat = settings.filterRatio / FILTER_RATIO_DIVIDER;
                    success = true;
                }
            }
            break;

        case WRITE_HISTORY_EXPIRE_DURATION:
            if (readAndValidateIoBuffer(WRITE_HISTORY_EXPIRE_DURATION, 2))
            {
                history.expireDuration = ioBufferRead16();
                writeWordToEeprom(EEPROM_ADRW_EXPIRE, history.expireDuration);
                success = true;
            }
            break;

        case MARK_START_TIME:  // mark base time for returned lap-ms-since-start values
            state.raceStartTimeStamp = millis();
            // make sure there's no lingering previous timestamp:
            lastPass.timeStamp = state.raceStartTimeStamp;
            // reset history
            history.peakFirstTime = state.raceStartTimeStamp;
            history.peakLastTime = state.raceStartTimeStamp;
            history.rssiMin = 999;
            history.minExpires = 0;
            history.rssiMax = 0;
            history.rssiPeak = 0;
            history.maxExpires = 0;

            if (readAndValidateIoBuffer(MARK_START_TIME, 1))  // read byte value (not used)
                success = true;
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
        Serial.print("RX Fault command: ");
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
            ioBufferWrite32(lastPass.timeStamp - state.raceStartTimeStamp);  // lap ms-since-start
            ioBufferWrite16(state.rssi);
            ioBufferWrite16(state.nodeRssiPeak);
            ioBufferWrite16(lastPass.rssiPeak);  // RSSI peak for last lap pass
            ioBufferWrite32(state.loopTime);
            ioBufferWrite8(state.crossing ? (uint8_t) 1 : (uint8_t) 0);  // 'crossing' status
            ioBufferWrite16(lastPass.rssiNadir);  // lowest rssi since end of last pass
            ioBufferWrite16(state.nodeRssiNadir);
            break;

        case READ_ENTER_AT_LEVEL:  // lap pass begins when RSSI is at or above this level
            ioBufferWrite16(settings.enterAtLevel);
            break;

        case READ_EXIT_AT_LEVEL:  // lap pass ends when RSSI goes below this level
            ioBufferWrite16(settings.exitAtLevel);
            break;

        case READ_FILTER_RATIO:
            ioBufferWrite16(settings.filterRatio);
            break;

        case READ_HISTORY_EXPIRE_DURATION:
            ioBufferWrite16(history.expireDuration);
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

        case READ_CATCH_HISTORY:  // manual pass catching
            // calculate timestamp from history only on demand
            uint32_t lapTimeStamp;
            lapTimeStamp = ((history.peakLastTime + history.peakFirstTime) / 2) - state.raceStartTimeStamp;

            ioBufferWrite16(history.rssiMin);
            ioBufferWrite16(history.rssiMax);
            ioBufferWrite32(lapTimeStamp);  // lap ms-since-start
            break;

        default:  // If an invalid command is sent, write nothing back, master must react
            Serial.print("TX Fault command: ");
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
