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

#include "config.h"
#include <Wire.h>
#include "clock.h"
#include "rssi.h"
#include "commands.h"
#include "rheeprom.h"

// i2c address for node
// Node 1 = 8, Node 2 = 10, Node 3 = 12, Node 4 = 14
// Node 5 = 16, Node 6 = 18, Node 7 = 20, Node 8 = 22
uint8_t i2cSlaveAddress = 6 + (NODE_NUMBER * 2);

#define EEPROM_ADRW_RXFREQ 0       //address for stored RX frequency value
#define EEPROM_ADRW_ENTERAT 2      //address for stored 'enterAtLevel'
#define EEPROM_ADRW_EXITAT 4       //address for stored 'exitAtLevel'
#define EEPROM_ADRW_EXPIRE 6       //address for stored catch history expire duration
#define EEPROM_ADRW_CHECKWORD 8    //address for integrity-check value
#define EEPROM_CHECK_VALUE 0x3526  //EEPROM integrity-check value
#define EEPROM_SETTINGS_SIZE 16

#define COMMS_MONITOR_TIME_MS 5000 //I2C communications monitor grace/trigger time

// dummy macro
#define LOG_ERROR(...)

Message i2cMessage(RssiReceivers::rssiRxs), serialMessage(RssiReceivers::rssiRxs);

// Defines for fast ADC reads
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))

void i2cInitialize(bool delayFlag);
void i2cReceive(int byteCount);
bool i2cReadAndValidateIoBuffer(byte expectedSize);
void i2cTransmit();

#if (!defined(NODE_NUMBER)) || (!NODE_NUMBER)
// Configure the I2C address based on input-pin level.
void configI2cSlaveAddress()
{
    // current hardware selection
    pinMode(HARDWARE_SELECT_PIN_1, INPUT_PULLUP);
    pinMode(HARDWARE_SELECT_PIN_2, INPUT_PULLUP);
    pinMode(HARDWARE_SELECT_PIN_3, INPUT_PULLUP);
    // legacy selection - DEPRECATED
    pinMode(LEGACY_HARDWARE_SELECT_PIN_1, INPUT_PULLUP);
    pinMode(LEGACY_HARDWARE_SELECT_PIN_2, INPUT_PULLUP);
    pinMode(LEGACY_HARDWARE_SELECT_PIN_3, INPUT_PULLUP);
    pinMode(LEGACY_HARDWARE_SELECT_PIN_4, INPUT_PULLUP);
    pinMode(LEGACY_HARDWARE_SELECT_PIN_5, INPUT_PULLUP);

    delay(100);  // delay a bit a let pin levels settle before reading inputs

    // check if legacy spec pins are in use (2-5 only)
    if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_2) == LOW ||
        digitalRead(LEGACY_HARDWARE_SELECT_PIN_3) == LOW ||
        digitalRead(LEGACY_HARDWARE_SELECT_PIN_4) == LOW ||
        digitalRead(LEGACY_HARDWARE_SELECT_PIN_5) == LOW)
    {
        // legacy spec
        if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_1) == HIGH)
        {
            if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_2) == LOW)
                i2cSlaveAddress = 8;
            else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_3) == LOW)
                i2cSlaveAddress = 10;
            else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_4) == LOW)
                i2cSlaveAddress = 12;
            else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_5) == LOW)
                i2cSlaveAddress = 14;
        }
        else
        {
            if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_2) == LOW)
                i2cSlaveAddress = 16;
            else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_3) == LOW)
                i2cSlaveAddress = 18;
            else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_4) == LOW)
                i2cSlaveAddress = 20;
            else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_5) == LOW)
                i2cSlaveAddress = 22;
        }
    }
    else
    {   // use standard selection
        i2cSlaveAddress = 0;
        if (digitalRead(HARDWARE_SELECT_PIN_1) == LOW)
            i2cSlaveAddress |= 1;
        if (digitalRead(HARDWARE_SELECT_PIN_2) == LOW)
            i2cSlaveAddress |= 2;
        if (digitalRead(HARDWARE_SELECT_PIN_3) == LOW)
            i2cSlaveAddress |= 4;
        i2cSlaveAddress = 8 + (i2cSlaveAddress * 2);
    }
}
#endif  // (!defined(NODE_NUMBER)) || (!NODE_NUMBER)

// Initialize program
void setup()
{
    // initialize pins for RX5808 module communications
    pinMode(RX5808_SEL_PIN, OUTPUT);
    pinMode(RX5808_DATA_PIN, OUTPUT);
    pinMode(RX5808_CLK_PIN, OUTPUT);
    digitalWrite(RX5808_SEL_PIN, HIGH);
    digitalWrite(RX5808_DATA_PIN, LOW);
    digitalWrite(RX5808_CLK_PIN, LOW);

    // init pin used to reset paired Arduino via RESET_PAIRED_NODE command
    pinMode(NODE_RESET_PIN, INPUT_PULLUP);

    // init pin that can be pulled low (to GND) to disable serial port
    pinMode(DISABLE_SERIAL_PIN, INPUT_PULLUP);

#if (!defined(NODE_NUMBER)) || (!NODE_NUMBER)
    configI2cSlaveAddress();
#else
    delay(100);  // delay a bit a let pin level settle before reading input
#endif

    if (digitalRead(DISABLE_SERIAL_PIN) == HIGH)
    {
        Serial.begin(SERIAL_BAUD_RATE);  // Start serial interface
        while (!Serial) {};  // Wait for the Serial port to initialize
    }

    i2cInitialize(false);  // setup I2C slave address and callbacks

    // set ADC prescaler to 16 to speedup ADC readings
    sbi(ADCSRA, ADPS2);
    cbi(ADCSRA, ADPS1);
    cbi(ADCSRA, ADPS0);

    // if EEPROM-check value matches then read stored values
    for (int i=0; i<RssiReceivers::rssiRxs->getCount(); i++) {
      Settings& settings = RssiReceivers::rssiRxs->getSettings(i);
      int offset = i*EEPROM_SETTINGS_SIZE;
      if (eepromReadWord(offset + EEPROM_ADRW_CHECKWORD) == EEPROM_CHECK_VALUE)
      {
          settings.vtxFreq = eepromReadWord(offset + EEPROM_ADRW_RXFREQ);
          settings.enterAtLevel = eepromReadWord(offset + EEPROM_ADRW_ENTERAT);
          settings.exitAtLevel = eepromReadWord(offset + EEPROM_ADRW_EXITAT);
      }
      else
      {    // if no match then initialize EEPROM values
          eepromWriteWord(offset + EEPROM_ADRW_RXFREQ, settings.vtxFreq);
          eepromWriteWord(offset + EEPROM_ADRW_ENTERAT, settings.enterAtLevel);
          eepromWriteWord(offset + EEPROM_ADRW_EXITAT, settings.exitAtLevel);
          eepromWriteWord(offset + EEPROM_ADRW_CHECKWORD, EEPROM_CHECK_VALUE);
      }

      RxModule& rx = RssiReceivers::rssiRxs->getRxModule(i);
      rx.reset(); 
      if (settings.vtxFreq == 1111) // frequency value to power down rx module
      {
          rx.powerDown();
      }
      else
      {
          rx.setFrequency(settings.vtxFreq);  // Setup rx module to default frequency
      }
    }

    RssiReceivers::rssiRxs->start();
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

static bool commsMonitorEnabledFlag = false;
static mtime_t commsMonitorLastResetTime = 0;

// Main loop
void loop()
{
    const uint32_t elapsed = usclock.tick();
    if (elapsed > 1000)
    {  // limit to once per millisecond
        // read raw RSSI close to taking timestamp
        const mtime_t ms = usclock.millis();
        bool crossingFlag = RssiReceivers::rssiRxs->readRssi();

        // update settings and status LED

        RssiNode& rssiNode = RssiReceivers::rssiRxs->getRssiNode(cmdRssiNodeIndex);
        State& state = rssiNode.getState();
        Settings& settings = rssiNode.getSettings();
        RxModule& rx = RssiReceivers::rssiRxs->getRxModule(cmdRssiNodeIndex);

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
            if (newVtxFreq == 1111) // frequency value to power down rx module
            {
                rx.powerDown();
            }
            else
            {
                if (rx.isPoweredDown())
                {
                    rx.reset();
                }
                rx.setFrequency(newVtxFreq);
            }
            
            state.activatedFlag = true;

            if (changeFlags & FREQ_CHANGED)
            {
                eepromWriteWord(EEPROM_ADRW_RXFREQ, newVtxFreq);
                rssiNode.resetState();  // restart rssi peak tracking for node
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
        byte expectedSize = i2cMessage.getPayloadSize();
        if (expectedSize > 0 && i2cReadAndValidateIoBuffer(expectedSize))
        {
            i2cMessage.handleWriteCommand(false);
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

    checksum = i2cMessage.buffer.calculateChecksum(expectedSize);

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
    i2cMessage.handleReadCommand(false);

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
            byte expectedSize = serialMessage.getPayloadSize();
            if (expectedSize > 0)
            {
                serialMessage.buffer.index = 0;
                serialMessage.buffer.size = expectedSize + 1;  // include checksum byte
            }
        }
        else
        {
            serialMessage.handleReadCommand(true);

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
            uint8_t checksum = serialMessage.buffer.calculateChecksum(serialMessage.buffer.size - 1);
            if (serialMessage.buffer.data[serialMessage.buffer.size - 1] == checksum)
            {
                serialMessage.handleWriteCommand(true);
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
