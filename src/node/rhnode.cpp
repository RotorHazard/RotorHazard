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
#include "i2c.h"
#include "wifi.h"
#include "hardware.h"

// Initialize program
void setup()
{
    hardware.init();

#ifdef USE_WIFI
    wifiInit();
#endif

    // if EEPROM-check value matches then read stored values
    for (int i=0; i<rssiRxs.getCount(); i++) {
        RxModule& rx = rssiRxs.getRxModule(i);
        hardware.initRxModule(i, rx);
        rx.reset();

        Settings& settings = rssiRxs.getSettings(i);
        hardware.initSettings(i, settings);
        if (settings.vtxFreq == POWER_OFF_FREQ)
        {
            rx.powerDown();
        }
        else if (settings.vtxFreq > 0)
        {
            rx.setFrequency(settings.vtxFreq);
        }
    }

    rssiRxs.start(usclock.millis(), usclock);
}

static utime_t previousTick = 0;
static uint_fast8_t currentStatusFlags = 0;

// Main loop
void loop()
{
    const utime_t us = usclock.tickMicros();
    // unsigned arithmetic to handle roll-over
    if ((us - previousTick) >= 1000)  // limit to once per millisecond
    {
        const mtime_t ms = usclock.millis();
        const bool crossingFlag = rssiRxs.readRssi(ms, usclock);
        previousTick = us;

        // update settings and status LED

        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            currentStatusFlags |= cmdStatusFlags;
            cmdStatusFlags = NO_STATUS;
        }

        // allow READ_LAP_STATS command to activate operations
        //  so they will resume after node or I2C bus reset
        RssiNode& cmdNode = rssiRxs.getRssiNode(cmdRssiNodeIndex);
        if (!cmdNode.active && (currentStatusFlags & POLLING))
        {
            cmdNode.active = true;
        }

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

#ifdef USE_I2C
    i2cEventRun();
#endif
#ifdef USE_WIFI
    wifiEventRun();
#endif
}

void handleStatusMessage(uint8_t msgType, uint8_t data)
{
  
}
