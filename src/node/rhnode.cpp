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

#if TARGET == STM32_TARGET
#include "stm32_hardware.h"
#elif TARGET == AVR_TARGET
#include "avr_hardware.h"
#elif TARGET == TEST_TARGET
#include "test_hardware.h"
#elif TARGET == SIL_TARGET
#include "sil/sil_hardware.h"
#endif

#define TICK_FOR(expr)  usclock.tickMicros();expr

static void processPendingOps(mtime_t ms);

// Initialize program
void setup()
{
    hardware.init();

    // if EEPROM-check value matches then read stored values
    for (int i=0; i<rssiRxs.getCount(); i++) {
        RxModule& rx = rssiRxs.getRxModule(i);
        hardware.initRxModule(i, rx);
        while (!rx.reset()) {
            TICK_FOR(delay(1));
        }

        Settings& settings = rssiRxs.getSettings(i);
        hardware.initSettings(i, settings);
        if (settings.vtxFreq == 1111) // frequency value to power down rx module
        {
            while (!rx.powerDown()) {
                TICK_FOR(delay(1));
            }
        }
        else if (settings.vtxFreq > 0)
        {
            while (!rx.setFrequency(settings.vtxFreq)) {  // Setup rx module to default frequency
                TICK_FOR(delay(1));
            }
        }
    }

    rssiRxs.start(usclock.millis(), usclock.tickMicros());
}

static utime_t previousTick = 0;
static uint_fast8_t currentStatusFlags = 0;

// Main loop
void loop()
{
    #if TARGET == STM32_TARGET && SERIAL_TYPE == USB_SERIAL_TYPE
    serialEvent();
    #endif

    const utime_t us = usclock.tickMicros();
    // unsigned arithmetic to handle roll-over
    if ((us - previousTick) > 1000)  // limit to once per millisecond
    {
        const mtime_t ms = usclock.millis();
        const bool crossingFlag = rssiRxs.readRssi(ms, us);
        previousTick = us;

        // update settings and status LED

        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            currentStatusFlags |= cmdStatusFlags;
            cmdStatusFlags = 0;
        }

        // allow READ_LAP_STATS command to activate operations
        //  so they will resume after node or I2C bus reset
        RssiNode& cmdNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
        if (!cmdNode.active && (currentStatusFlags & POLLING))
        {
            cmdNode.active = true;
        }

        processPendingOps(ms);

        hardware.processStatusFlags(ms, currentStatusFlags);

        currentStatusFlags &= ~POLLING;
        currentStatusFlags &= ~SERIAL_CMD_MSG;

        // Status LED
        if (ms <= 1000)
        {  //flash three times during first second of running
            int ti = (int)(ms / 100);
            hardware.setStatusLed(ti != 3 && ti != 7);
        }
        else if ((int)(ms % 20) == 0)
        {  //only run every 20ms so flashes last longer (brighter)

            // if crossing or communications activity then LED on
            if (crossingFlag)
            {
                hardware.setStatusLed(true);
            }
            else if (currentStatusFlags & COMM_ACTIVITY)
            {
                hardware.setStatusLed(true);
                currentStatusFlags &= ~COMM_ACTIVITY;  // clear COMM_ACTIVITY flag
            }
            else
            {
                hardware.setStatusLed(ms % 2000 == 0);  // blink
            }
        }
    }
}

void processPendingOps(mtime_t ms) {
    for (int_fast8_t i=rssiRxs.getCount()-1; i>=0; i--) {
        RssiNode& node = rssiRxs.getRssiNode(i);

        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            node.pendingOps |= node.cmdPendingOps;
            node.cmdPendingOps = 0;
        }

        // update settings

        Settings& settings = node.getSettings();
        if (node.pendingOps & FREQ_SET) {
            // disable node until frequency change complete
            node.active = false;

            freq_t newVtxFreq;
            ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
            {
                newVtxFreq = settings.vtxFreq;
            }
            RxModule& rx = rssiRxs.getRxModule(i);
            if (newVtxFreq == 1111) { // frequency value to power down rx module
                if (rx.isPoweredDown() || rx.powerDown()) {
                    node.pendingOps &= ~FREQ_SET;
                }
            } else {
                if (rx.isPoweredDown()) {
                    rx.reset();
                }
                if (!rx.isPoweredDown() && rx.setFrequency(newVtxFreq)) {
                    // frequency change complete - re-enable node
                    node.active = true;
                    node.pendingOps &= ~FREQ_SET;
                }
            }

            if (node.pendingOps & FREQ_CHANGED) {
                if (settings.mode != SCANNER) {
                    hardware.storeFrequency(newVtxFreq);
                }
                node.resetState(ms);  // restart rssi peak tracking for node
                node.pendingOps &= ~FREQ_CHANGED;
            }
        }

        if (node.pendingOps & ENTERAT_CHANGED) {
            hardware.storeEnterAtLevel(settings.enterAtLevel);
            node.pendingOps &= ~ENTERAT_CHANGED;
        }

        if (node.pendingOps & EXITAT_CHANGED) {
            hardware.storeExitAtLevel(settings.exitAtLevel);
            node.pendingOps &= ~EXITAT_CHANGED;
        }
    }
}

void handleStatusMessage(uint8_t msgType, uint8_t data)
{
  
}
