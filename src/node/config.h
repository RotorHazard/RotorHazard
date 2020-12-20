#ifndef config_h
#define config_h

#include <Arduino.h>
#include "util/rhtypes.h"

// ******************************************************************** //

// *** Node Setup - Set node number here (1-8): ***
#define NODE_NUMBER 0

// Set to 1-8 for manual selection.

// Set to 0 for automatic selection via hardware pin.
// See https://github.com/RotorHazard/RotorHazard/wiki/Specification:-Node-hardware-addressing

// ******************************************************************** //

#ifdef STM32_CORE_VERSION
#define STM32_MODE_FLAG 1  // 1 for STM 32-bit processor running multiple nodes
#else
#define STM32_MODE_FLAG 0  // 0 for Arduino processor running single node
#endif

#define STM32_SERIALUSB_FLAG 0

// features flags for value returned by READ_RHFEAT_FLAGS command
#define RHFEAT_STM32_MODE ((uint16_t)0x0004)      // STM 32-bit processor running multiple nodes
#define RHFEAT_JUMPTO_BOOTLDR ((uint16_t)0x0008)  // JUMP_TO_BOOTLOADER command supported
#define RHFEAT_IAP_FIRMWARE ((uint16_t)0x0010)    // in-application programming of firmware supported
#define RHFEAT_NONE ((uint16_t)0)

#if STM32_MODE_FLAG
// value returned by READ_RHFEAT_FLAGS command
#define RHFEAT_FLAGS_VALUE (RHFEAT_STM32_MODE | RHFEAT_JUMPTO_BOOTLDR | RHFEAT_IAP_FIRMWARE)

#define SERIAL_BAUD_RATE 921600
#define MULTI_RHNODE_MAX 2

#else
// value returned by READ_RHFEAT_FLAGS command
#define RHFEAT_FLAGS_VALUE RHFEAT_NONE

#define SERIAL_BAUD_RATE 115200
#define MULTI_RHNODE_MAX 1
#endif


#if STM32_MODE_FLAG || defined(__TEST__)
#define ATOMIC_BLOCK(x)
#define ATOMIC_RESTORESTATE
#else
#include <util/atomic.h>
#endif

// Set to 0 for standard RotorHazard USB node wiring; set to 1 for ArduVidRx USB node wiring
//   See here for an ArduVidRx example: http://www.etheli.com/ArduVidRx/hw/index.html#promini
#define ARDUVIDRX_WIRING_FLAG 0

#define CHORUS_WIRING_FLAG 0

#if ARDUVIDRX_WIRING_FLAG
#define RX5808_DATA_PIN 10             //DATA output line to RX5808 module
#define RX5808_SEL_PIN 11              //CLK output line to RX5808 module
#define RX5808_CLK_PIN 12              //SEL output line to RX5808 module
#define RSSI_INPUT_PIN A7              //RSSI input from RX5808
#define NODE_RESET_PIN A1              //Pin to reset paired Arduino via command for ISP
#elif CHORUS_WIRING_FLAG
#define RX5808_DATA_PIN 10             //DATA output line to RX5808 module
#define RX5808_SEL_PIN 11              //CLK output line to RX5808 module
#define RX5808_CLK_PIN 12              //SEL output line to RX5808 module
#define RSSI_INPUT_PIN A3              //RSSI input from RX5808
#define NODE_RESET_PIN A1              //Pin to reset paired Arduino via command for ISP
#else
#define RX5808_DATA_PIN 11             //DATA output line to RX5808 module
#define RX5808_SEL_PIN 10              //CLK output line to RX5808 module
#define RX5808_CLK_PIN 13              //SEL output line to RX5808 module
#define RSSI_INPUT_PIN A0              //RSSI input from RX5808
#define NODE_RESET_PIN 12              //Pin to reset paired Arduino via command for ISP
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

#endif  // config_h
