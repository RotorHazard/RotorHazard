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
#include "microclock.h"
#include "rssi.h"
#include "commands.h"

// Note: Configure Arduino NODE_NUMBER value in 'config.h'

// dummy macro
#define LOG_ERROR(...)

#if defined(__TEST__)
#include "test_hardware.h"
#else
#if STM32_MODE_FLAG
#include "stm32_hardware.h"
#else
#include "avr_hardware.h"
#endif
#endif

// Initialize program
void setup()
{
    hardware->init();

    // if EEPROM-check value matches then read stored values
    for (int i=0; i<RssiReceivers::rssiRxs->getCount(); i++) {
        RxModule& rx = RssiReceivers::rssiRxs->getRxModule(i);
        hardware->initRxModule(i, rx);
        while (!rx.reset()) {
            delay(1);
        }

        Settings& settings = RssiReceivers::rssiRxs->getSettings(i);
        hardware->initSettings(i, settings);
        if (settings.vtxFreq == 1111) // frequency value to power down rx module
        {
            while (!rx.powerDown()) {
                delay(1);
            }
        }
        else if (settings.vtxFreq > 0)
        {
            while (!rx.setFrequency(settings.vtxFreq)) {  // Setup rx module to default frequency
                delay(1);
            }
        }
    }

    RssiReceivers::rssiRxs->start();
}

static uint32_t elapsedSinceLastRead = 0;
static uint8_t currentStatusFlags = 0;

// Main loop
void loop()
{
    const uint32_t elapsedSinceLastTick = usclock.tick();
    elapsedSinceLastRead += elapsedSinceLastTick;
    if (elapsedSinceLastRead > 1000)
    {  // limit to once per millisecond
        bool crossingFlag = RssiReceivers::rssiRxs->readRssi();
        elapsedSinceLastRead = 0;

        // update settings and status LED

        RssiNode& rssiNode = RssiReceivers::rssiRxs->getRssiNode(cmdRssiNodeIndex);
        State& state = rssiNode.getState();
        Settings& settings = rssiNode.getSettings();
        RxModule& rx = RssiReceivers::rssiRxs->getRxModule(cmdRssiNodeIndex);

        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            currentStatusFlags |= cmdStatusFlags;
            cmdStatusFlags = 0;
        }

        // allow READ_LAP_STATS command to activate operations
        //  so they will resume after node or I2C bus reset
        if (!state.activatedFlag && (currentStatusFlags & LAPSTATS_READ))
        {
            state.activatedFlag = true;
        }

        // update settings

        if (currentStatusFlags & FREQ_SET)
        {
            uint16_t newVtxFreq;
            ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
            {
                newVtxFreq = settings.vtxFreq;
            }
            if (newVtxFreq == 1111) // frequency value to power down rx module
            {
                if (rx.isPoweredDown() || rx.powerDown())
                {
                    currentStatusFlags &= ~FREQ_SET;
                }
                state.activatedFlag = false;
            }
            else
            {
                if (rx.isPoweredDown())
                {
                    rx.reset();
                }
                if (!rx.isPoweredDown() && rx.setFrequency(newVtxFreq))
                {
                    currentStatusFlags &= ~FREQ_SET;
                }
                state.activatedFlag = true;
            }

            if (currentStatusFlags & FREQ_CHANGED)
            {
                hardware->storeFrequency(newVtxFreq);
                rssiNode.resetState();  // restart rssi peak tracking for node
                currentStatusFlags &= ~FREQ_CHANGED;
            }
        }

        if (currentStatusFlags & ENTERAT_CHANGED)
        {
            hardware->storeEnterAtLevel(settings.enterAtLevel);
            currentStatusFlags &= ~ENTERAT_CHANGED;
        }

        if (currentStatusFlags & EXITAT_CHANGED)
        {
            hardware->storeExitAtLevel(settings.exitAtLevel);
            currentStatusFlags &= ~EXITAT_CHANGED;
        }

        hardware->processStatusFlags(currentStatusFlags, rssiNode);
        currentStatusFlags &= ~LAPSTATS_READ;
        currentStatusFlags &= ~SERIAL_CMD_MSG;

        // Status LED
        mtime_t ms = millis();
        if (ms <= 1000)
        {  //flash three times during first second of running
            int ti = (int)ms / 100;
            hardware->setStatusLed(ti != 3 && ti != 7);
        }
        else if ((int)(ms % 20) == 0)
        {  //only run every 20ms so flashes last longer (brighter)

            // if crossing or communications activity then LED on
            if (crossingFlag)
            {
                hardware->setStatusLed(true);
            }
            else if (currentStatusFlags & COMM_ACTIVITY)
            {
                hardware->setStatusLed(true);
                currentStatusFlags &= ~COMM_ACTIVITY;  // clear COMM_ACTIVITY flag
            }
            else
            {
                hardware->setStatusLed(ms % 2000 == 0);  // blink
            }
        }
    }
}
