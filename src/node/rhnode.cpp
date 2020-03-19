#ifndef __TEST__
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

#include <Arduino.h>
#include <util/atomic.h>
#include <Wire.h>
#include "rhtypes.h"
#include "rssi.h"
#include "commands.h"
#include "rheeprom.h"

// ******************************************************************** //

// *** Node Setup - Set node number here (1-8): ***
#define NODE_NUMBER 0

// Set to 1-8 for manual selection.
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
uint8_t i2cSlaveAddress = 6 + (NODE_NUMBER * 2);

// Set to 0 for standard RotorHazard node wiring; set to 1 for ArduVidRx node wiring
//   See here for an ArduVidRx example: http://www.etheli.com/ArduVidRx/hw/index.html#promini
#define ARDUVIDRX_WIRING_FLAG 0

#if !ARDUVIDRX_WIRING_FLAG
#define RX5808_DATA_PIN 11             //DATA output line to RX5808 module
#define RX5808_SEL_PIN 10              //CLK output line to RX5808 module
#define RX5808_CLK_PIN 13              //SEL output line to RX5808 module
#define RSSI_INPUT_PIN 0               //RSSI input from RX5808 (primary)
#else
#define RX5808_DATA_PIN 10             //DATA output line to RX5808 module
#define RX5808_SEL_PIN 11              //CLK output line to RX5808 module
#define RX5808_CLK_PIN 12              //SEL output line to RX5808 module
#define RSSI_INPUT_PIN A7              //RSSI input from RX5808 (primary)
#endif


#define EEPROM_ADRW_RXFREQ 0       //address for stored RX frequency value
#define EEPROM_ADRW_ENTERAT 2      //address for stored 'enterAtLevel'
#define EEPROM_ADRW_EXITAT 4       //address for stored 'exitAtLevel'
#define EEPROM_ADRW_EXPIRE 6       //address for stored catch history expire duration
#define EEPROM_ADRW_CHECKWORD 8    //address for integrity-check value
#define EEPROM_CHECK_VALUE 0x3526  //EEPROM integrity-check value

#define COMMS_MONITOR_TIME_MS 5000 //I2C communications monitor grace/trigger time

// dummy macro
#define LOG_ERROR(...)


static Message_t i2cMessage, serialMessage;

// Defines for fast ADC reads
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))

void i2cInitialize(bool delayFlag);
void i2cReceive(int byteCount);
bool i2cReadAndValidateIoBuffer(byte expectedSize);
void i2cTransmit();
void setRxModule(uint16_t frequency);

// Initialize program
void setup()
{
    if (!NODE_NUMBER)
    {
        pinMode(4, INPUT_PULLUP);
        pinMode(5, INPUT_PULLUP);
        pinMode(6, INPUT_PULLUP);
        pinMode(7, INPUT_PULLUP);
        pinMode(8, INPUT_PULLUP);

        if (digitalRead(4) == HIGH)
        {
            if (digitalRead(5) == LOW)
            {
                i2cSlaveAddress = 8;
            }
            else if (digitalRead(6) == LOW)
            {
                i2cSlaveAddress = 10;
            }
            else if (digitalRead(7) == LOW)
            {
                i2cSlaveAddress = 12;
            }
            else if (digitalRead(8) == LOW)
            {
                i2cSlaveAddress = 14;
            }
        }
        else
        {
            if (digitalRead(5) == LOW)
            {
                i2cSlaveAddress = 16;
            }
            else if (digitalRead(6) == LOW)
            {
                i2cSlaveAddress = 18;
            }
            else if (digitalRead(7) == LOW)
            {
                i2cSlaveAddress = 20;
            }
            else if (digitalRead(8) == LOW)
            {
                i2cSlaveAddress = 22;
            }
        }
    }

    Serial.begin(115200);  // Start serial interface

    pinMode(RX5808_SEL_PIN, OUTPUT);  // RX5808 comms
    pinMode(RX5808_DATA_PIN, OUTPUT);
    pinMode(RX5808_CLK_PIN, OUTPUT);
    digitalWrite(RX5808_SEL_PIN, HIGH);

    while (!Serial)
    {
    };  // Wait for the Serial port to initialise

    i2cInitialize(false);  // setup I2C slave address and callbacks

    // set ADC prescaler to 16 to speedup ADC readings
    sbi(ADCSRA, ADPS2);
    cbi(ADCSRA, ADPS1);
    cbi(ADCSRA, ADPS0);

    // if EEPROM-check value matches then read stored values
    if (eepromReadWord(EEPROM_ADRW_CHECKWORD) == EEPROM_CHECK_VALUE)
    {
        settings.vtxFreq = eepromReadWord(EEPROM_ADRW_RXFREQ);
        settings.enterAtLevel = eepromReadWord(EEPROM_ADRW_ENTERAT);
        settings.exitAtLevel = eepromReadWord(EEPROM_ADRW_EXITAT);
    }
    else
    {    // if no match then initialize EEPROM values
        eepromWriteWord(EEPROM_ADRW_RXFREQ, settings.vtxFreq);
        eepromWriteWord(EEPROM_ADRW_ENTERAT, settings.enterAtLevel);
        eepromWriteWord(EEPROM_ADRW_EXITAT, settings.exitAtLevel);
        eepromWriteWord(EEPROM_ADRW_CHECKWORD, EEPROM_CHECK_VALUE);
    }

    setRxModule(settings.vtxFreq);  // Setup rx module to default frequency

    rssiInit();
}

// Functions for the rx5808 module

void SERIAL_SENDBIT1()
{
    digitalWrite(RX5808_CLK_PIN, LOW);
    delayMicroseconds(300);
    digitalWrite(RX5808_DATA_PIN, HIGH);
    delayMicroseconds(300);
    digitalWrite(RX5808_CLK_PIN, HIGH);
    delayMicroseconds(300);
    digitalWrite(RX5808_CLK_PIN, LOW);
    delayMicroseconds(300);
}

void SERIAL_SENDBIT0()
{
    digitalWrite(RX5808_CLK_PIN, LOW);
    delayMicroseconds(300);
    digitalWrite(RX5808_DATA_PIN, LOW);
    delayMicroseconds(300);
    digitalWrite(RX5808_CLK_PIN, HIGH);
    delayMicroseconds(300);
    digitalWrite(RX5808_CLK_PIN, LOW);
    delayMicroseconds(300);
}

void SERIAL_ENABLE_LOW()
{
    delayMicroseconds(100);
    digitalWrite(RX5808_SEL_PIN, LOW);
    delayMicroseconds(100);
}

void SERIAL_ENABLE_HIGH()
{
    delayMicroseconds(100);
    digitalWrite(RX5808_SEL_PIN, HIGH);
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
void setRxModule(uint16_t frequency)
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

    digitalWrite(RX5808_SEL_PIN, LOW);
    digitalWrite(RX5808_CLK_PIN, LOW);
    digitalWrite(RX5808_DATA_PIN, LOW);
}

// Read the RSSI value for the current channel
rssi_t rssiRead()
{
    // reads 5V value as 0-1023, RX5808 is 3.3V powered so RSSI pin will never output the full range
    int raw = analogRead(RSSI_INPUT_PIN);
    // clamp upper range to fit scaling
    if (raw > 0x01FF)
        raw = 0x01FF;
    // rescale to fit into a byte and remove some jitter
    return raw >> 1;
}

static bool currentStatusLedFlag = false;

void setStatusLed(bool onFlag)
{
    if (onFlag)
    {
        if (!currentStatusLedFlag)
        {
            currentStatusLedFlag = true;
            digitalWrite(LED_BUILTIN, HIGH);
        }
    }
    else
    {
        if (currentStatusLedFlag)
        {
            currentStatusLedFlag = false;
            digitalWrite(LED_BUILTIN, LOW);
        }
    }
}

static mtime_t loopMillis = 0;
static bool commsMonitorEnabledFlag = false;
static mtime_t commsMonitorLastResetTime = 0;

// Main loop
void loop()
{
    mtime_t ms = millis();
    if (ms > loopMillis)
    {  // limit to once per millisecond
        // read raw RSSI close to taking timestamp
        bool crossingFlag = rssiProcess(rssiRead(), ms);

        // update settings and status LED

        uint8_t changeFlags;
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            changeFlags = settingChangedFlags;
            settingChangedFlags &= COMM_ACTIVITY;  // clear all except COMM_ACTIVITY
        }
        bool oldActFlag = state.activatedFlag;
        if (changeFlags & FREQ_SET)
        {
            uint16_t newVtxFreq;
            ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
            {
                newVtxFreq = settings.vtxFreq;
            }
            setRxModule(newVtxFreq);
            state.activatedFlag = true;

            if (changeFlags & FREQ_CHANGED)
            {
                eepromWriteWord(EEPROM_ADRW_RXFREQ, newVtxFreq);
                rssiStateReset();  // restart rssi peak tracking for node
            }
        }

        // also allow READ_LAP_STATS command to activate operations
        //  so they will resume after node or I2C bus reset
        if (!state.activatedFlag && (changeFlags & LAPSTATS_READ))
            state.activatedFlag = true;

        if (commsMonitorEnabledFlag)
        {
            if (changeFlags & COMM_ACTIVITY)
            {  //communications activity detected; update comms monitor time
                commsMonitorLastResetTime = ms;
            }
            else if (ms - commsMonitorLastResetTime > COMMS_MONITOR_TIME_MS)
            {  //too long since last communications activity detected
                commsMonitorEnabledFlag = false;
                // redo init, which should release I2C pins (SDA & SCL) if "stuck"
                i2cInitialize(true);
            }
        }
        else if (oldActFlag && (changeFlags & LAPSTATS_READ) &&
                (changeFlags & SERIAL_CMD_MSG) == (uint8_t)0)
        {  //if activated and I2C LAPSTATS_READ cmd received then enable comms monitor
            commsMonitorEnabledFlag = true;
            commsMonitorLastResetTime = ms;
        }

        if (changeFlags & ENTERAT_CHANGED)
            eepromWriteWord(EEPROM_ADRW_ENTERAT, settings.enterAtLevel);

        if (changeFlags & EXITAT_CHANGED)
            eepromWriteWord(EEPROM_ADRW_EXITAT, settings.exitAtLevel);

        // Status LED
        if (ms <= 1000)
        {  //flash three times during first second of running
            int ti = (int)ms / 100;
            setStatusLed(ti != 3 && ti != 7);
        }
        else if ((int)(ms % 20) == 0)
        {  //only run every 20ms so flashes last longer (brighter)

            // if crossing or communications activity then LED on
            if (crossingFlag)
                setStatusLed(true);
            else if (changeFlags & COMM_ACTIVITY)
            {
                setStatusLed(true);
                settingChangedFlags = 0;  // clear COMM_ACTIVITY flag
            }
            else
                setStatusLed(ms % 2000 == 0);  // blink
        }

        loopMillis = ms;
    }
}

void i2cInitialize(bool delayFlag)
{
    setStatusLed(true);
    Wire.end();  // release I2C pins (SDA & SCL), in case they are "stuck"
    if (delayFlag)   // do delay if called via comms monitor
        delay(250);  //  to help bus reset and show longer LED flash
    setStatusLed(false);

    Wire.begin(i2cSlaveAddress);  // I2C slave address setup
    Wire.onReceive(i2cReceive);   // Trigger 'i2cReceive' function on incoming data
    Wire.onRequest(i2cTransmit);  // Trigger 'i2cTransmit' function for outgoing data, on master request

    TWAR = (i2cSlaveAddress << 1) | 1;  // enable broadcasts to be received
}

// Function called by twi interrupt service when master sends information to the slave
// or when master sets up a specific read request
void i2cReceive(int byteCount)
{  // Number of bytes in rx buffer
   // If byteCount is zero, the master only checked for presence of the slave device, no response necessary
    if (byteCount == 0)
    {
        LOG_ERROR("no bytes to receive?");
        return;
    }

    if (byteCount != Wire.available())
    {
        LOG_ERROR("rx byte count and wire available don't agree");
    }

    i2cMessage.command = Wire.read();  // The first byte sent is a command byte

    if (i2cMessage.command > 0x50)
    {  // Commands > 0x50 are writes TO this slave
        byte expectedSize = getPayloadSize(i2cMessage.command);
        if (expectedSize > 0 && i2cReadAndValidateIoBuffer(expectedSize))
        {
            handleWriteCommand(&i2cMessage, false);
        }
        i2cMessage.buffer.size = 0;
    }
    else
    {  // Otherwise this is a request FROM this device
        if (Wire.available())
        {  // There shouldn't be any data present on the line for a read request
            LOG_ERROR("Wire.available() on a read request.", ioCommand, HEX);
            while (Wire.available())
            {
                Wire.read();
            }
        }
    }
}

bool i2cReadAndValidateIoBuffer(byte expectedSize)
{
    uint8_t checksum;

    for (i2cMessage.buffer.size = 0; i2cMessage.buffer.size < expectedSize + 1;
            i2cMessage.buffer.size++)
    {
        if (!Wire.available())
        {
            return false;
        }
        i2cMessage.buffer.data[i2cMessage.buffer.size] = Wire.read();
    }

    checksum = ioCalculateChecksum(i2cMessage.buffer.data, expectedSize);

    if (i2cMessage.buffer.data[i2cMessage.buffer.size-1] == checksum)
    {
        return true;
    }
    else
    {
        LOG_ERROR("Invalid checksum", checksum);
        return false;
    }
}

// Function called by twi interrupt service when the Master wants to get data from the Slave
// No parameters and no returns
// A transmit buffer (ioBuffer) is populated with the data before sending.
void i2cTransmit()
{
    handleReadCommand(&i2cMessage, false);

    if (i2cMessage.buffer.size > 0)
    {  // If there is pending data, send it
        Wire.write((byte *)i2cMessage.buffer.data, i2cMessage.buffer.size);
        i2cMessage.buffer.size = 0;
    }
}

void serialEvent()
{
    uint8_t nextByte = Serial.read();
    if (serialMessage.buffer.size == 0)
    {
        // new command
        serialMessage.command = nextByte;
        if (serialMessage.command > 0x50)
        {  // Commands > 0x50 are writes TO this slave
            byte expectedSize = getPayloadSize(serialMessage.command);
            if (expectedSize > 0)
            {
                serialMessage.buffer.index = 0;
                serialMessage.buffer.size = expectedSize + 1;  // include checksum byte
            }
        }
        else
        {
            handleReadCommand(&serialMessage, true);

            if (serialMessage.buffer.size > 0)
            {  // If there is pending data, send it
                Serial.write((byte *)serialMessage.buffer.data, serialMessage.buffer.size);
                serialMessage.buffer.size = 0;
            }
        }
    }
    else
    {
        // existing command
        serialMessage.buffer.data[serialMessage.buffer.index++] = nextByte;
        if (serialMessage.buffer.index == serialMessage.buffer.size)
        {
            uint8_t checksum = ioCalculateChecksum(serialMessage.buffer.data,
                    serialMessage.buffer.size - 1);
            if (serialMessage.buffer.data[serialMessage.buffer.size - 1] == checksum)
            {
                handleWriteCommand(&serialMessage, true);
            }
            else
            {
                LOG_ERROR("Invalid checksum", checksum);
            }
            serialMessage.buffer.size = 0;
        }
    }
}
#endif
