#ifndef config_h
#define config_h

#if !defined(__TEST__) && (defined(_WIN32) || defined(__linux__))
#include "sil/arduino.h"
#else
#include <Arduino.h>
#endif
#include "util/rhtypes.h"

#define AVR_TARGET 1
#define STM32_TARGET 2
#define ESP32_TARGET 3
#define SIL_TARGET 5
#define TEST_TARGET 0

#if defined(STM32_CORE_VERSION)
#define TARGET STM32_TARGET
#elif defined(ESP_PLATFORM)
#define TARGET ESP32_TARGET
#elif defined(__TEST__)
#define TARGET TEST_TARGET
#elif defined(_WIN32) || defined(__linux__)
#define TARGET SIL_TARGET
#else
#define TARGET AVR_TARGET
#endif

#if TARGET == AVR_TARGET

// Set to 1-8 for manual selection of Arduino node ID/address.
// Set to 0 for automatic selection via hardware pin.
// See https://github.com/RotorHazard/RotorHazard/wiki/Specification:-Node-hardware-addressing
#define NODE_NUMBER 0

#endif

// ******************************************************************** //

#define USB_SERIAL_TYPE 1
#define PIN_SERIAL_TYPE 2

#define SERIAL_TYPE USB_SERIAL_TYPE

#if TARGET == STM32_TARGET
    #define MULTI_RHNODE_MAX 8
    #define SERIAL_TYPE PIN_SERIAL_TYPE // USB_SERIAL_TYPE to use BPill USB port for serial link
#elif TARGET == ESP32_TARGET
    #define MULTI_RHNODE_MAX 6
#else
    #ifndef MULTI_RHNODE_MAX
        // Set greater than 1 to support multiple freqs per node
        #define MULTI_RHNODE_MAX 1
    #endif
#endif  // STM32_MODE_FLAG

// multi-freq reads
#define READS_PER_FREQ 64

#if TARGET == AVR_TARGET
#include <util/atomic.h>
#else
#define ATOMIC_BLOCK(x)
#define ATOMIC_RESTORESTATE
#endif

#if TARGET == AVR_TARGET
    #define RH_WIRING 0
    #define ARDUVIDRX_WIRING 1
    #define CHORUS_WIRING 2

    /*
       Set to RH_WIRING for standard RotorHazard USB node wiring;
       set to ARDUVIDRX_WIRING for ArduVidRx USB node wiring
       See here for an ArduVidRx example: http://www.etheli.com/ArduVidRx/hw/index.html#promini
     */
    #define WIRING_TYPE RH_WIRING

    #if WIRING_TYPE == RH_WIRING
        #define RX5808_DATA_PIN 11             //DATA output line to RX5808 module
        #define RX5808_SEL_PIN 10              //CLK output line to RX5808 module
        #define RX5808_CLK_PIN 13              //SEL output line to RX5808 module
        #define RSSI_INPUT_PIN A0              //RSSI input from RX5808
        #define NODE_RESET_PIN 12              //Pin to reset paired Arduino via command for ISP
    #elif WIRING_TYPE == ARDUVIDRX_WIRING
        #define RX5808_DATA_PIN 10             //DATA output line to RX5808 module
        #define RX5808_SEL_PIN 11              //CLK output line to RX5808 module
        #define RX5808_CLK_PIN 12              //SEL output line to RX5808 module
        #define RSSI_INPUT_PIN A7              //RSSI input from RX5808
        #define NODE_RESET_PIN A1              //Pin to reset paired Arduino via command for ISP
    #elif WIRING_TYPE == CHORUS_WIRING
        #define RX5808_DATA_PIN 10             //DATA output line to RX5808 module
        #define RX5808_SEL_PIN 11              //CLK output line to RX5808 module
        #define RX5808_CLK_PIN 12              //SEL output line to RX5808 module
        #define RSSI_INPUT_PIN A3              //RSSI input from RX5808
        #define NODE_RESET_PIN A1              //Pin to reset paired Arduino via command for ISP
    #endif

    #define DISABLE_SERIAL_PIN 9  //pull pin low (to GND) to disable serial port
    #define HARDWARE_SELECT_PIN_1 2
    #define HARDWARE_SELECT_PIN_2 3
    #define HARDWARE_SELECT_PIN_3 4
    #define LEGACY_HARDWARE_SELECT_PIN_1 4
    #define LEGACY_HARDWARE_SELECT_PIN_2 5
    #define LEGACY_HARDWARE_SELECT_PIN_3 6
    #define LEGACY_HARDWARE_SELECT_PIN_4 7
    #define LEGACY_HARDWARE_SELECT_PIN_5 8

#endif

// use persistent homology detection
#define USE_PH

#if TARGET == ESP32_TARGET
#define RX_IMPL NativeRxModule
#else
#define RX_IMPL BitBangRxModule
#endif

#if TARGET != AVR_TARGET || MULTI_RHNODE_MAX == 1
#define SCAN_HISTORY
#else
// uncomment to activate scanner mode
//#define SCAN_HISTORY
#endif
// uncomment to activate raw mode
//#define RSSI_HISTORY

#ifdef __TEST__
#undef USE_PH
#define SCAN_HISTORY
#define RSSI_HISTORY
#endif

#endif  // config_h
