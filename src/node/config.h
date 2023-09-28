#ifndef config_h
#define config_h

#include <Arduino.h>
#include "util/rhtypes.h"

#ifdef STM32_CORE_VERSION
#define STM32_MODE_FLAG 1  // 1 for STM 32-bit processor running multiple nodes
#else
#define STM32_MODE_FLAG 0  // 0 for Arduino processor running single node
#endif

#if !STM32_MODE_FLAG

// Set to 1-8 for manual selection of Arduino node ID/address
// Set to 0 for automatic selection via hardware pin
// See https://github.com/RotorHazard/RotorHazard/wiki/Specification:-Node-hardware-addressing
#define NODE_NUMBER 0
#define NODE_EEPROM 1 // Enable this value to read/write node number to eeprom memory

#endif

// ******************************************************************** //

// features flags for value returned by READ_RHFEAT_FLAGS command
#define RHFEAT_STM32_MODE ((uint16_t)0x0004)      // STM 32-bit processor running multiple nodes
#define RHFEAT_JUMPTO_BOOTLDR ((uint16_t)0x0008)  // JUMP_TO_BOOTLOADER command supported
#define RHFEAT_IAP_FIRMWARE ((uint16_t)0x0010)    // in-application programming of firmware supported
#define RHFEAT_NONE ((uint16_t)0)

#if STM32_MODE_FLAG
// value returned by READ_RHFEAT_FLAGS command
#define RHFEAT_FLAGS_VALUE (RHFEAT_STM32_MODE | RHFEAT_JUMPTO_BOOTLDR | RHFEAT_IAP_FIRMWARE)

#define SERIAL_BAUD_RATE 921600
#define MULTI_RHNODE_MAX 8
#define STM32_SERIALUSB_FLAG 0  // 1 to use BPill USB port for serial link

#else
// value returned by READ_RHFEAT_FLAGS command
#define RHFEAT_FLAGS_VALUE RHFEAT_NONE

#define SERIAL_BAUD_RATE 115200
#define MULTI_RHNODE_MAX 1
#endif  // STM32_MODE_FLAG


#if STM32_MODE_FLAG || defined(__TEST__)
#define ATOMIC_BLOCK(x)
#define ATOMIC_RESTORESTATE
#else
#include <util/atomic.h>
#endif

#if !STM32_MODE_FLAG

// Set to 0 for standard RotorHazard node wiring; set to 1 for ArduVidRx USB node wiring
//   See here for an ArduVidRx example: http://www.etheli.com/ArduVidRx/hw/index.html#promini
#define ARDUVIDRX_WIRING_FLAG 0

#define CHORUS_WIRING_FLAG 0

#if ARDUVIDRX_WIRING_FLAG
#define RX5808_DATA_PIN 10             //DATA output line to RX5808 module
#define RX5808_SEL_PIN 11              //SEL output line to RX5808 module
#define RX5808_CLK_PIN 12              //CLK output line to RX5808 module
#define RSSI_INPUT_PIN A7              //RSSI input from RX5808
#define NODE_RESET_PIN A1              //Pin to reset paired Arduino via command for ISP
#elif CHORUS_WIRING_FLAG
#define RX5808_DATA_PIN 10             //DATA output line to RX5808 module
#define RX5808_SEL_PIN 11              //SEL output line to RX5808 module
#define RX5808_CLK_PIN 12              //CLK output line to RX5808 module
#define RSSI_INPUT_PIN A3              //RSSI input from RX5808
#define NODE_RESET_PIN A1              //Pin to reset paired Arduino via command for ISP
#else
#define RX5808_DATA_PIN 11             //DATA output line to RX5808 module
#define RX5808_SEL_PIN 10              //SEL output line to RX5808 module
#define RX5808_CLK_PIN 13              //CLK output line to RX5808 module
#define RSSI_INPUT_PIN A0              //RSSI input from RX5808
#define NODE_RESET_PIN 12              //Pin to reset paired Arduino via command for ISP
#endif

#define DISABLE_SERIAL_PIN 9  //pull pin low (to GND) to disable serial port

#ifdef NODE_EEPROM
#define NODE_EEPROM_INPUT_PIN 2
#else
#define HARDWARE_SELECT_PIN_1 2
#define HARDWARE_SELECT_PIN_2 3
#define HARDWARE_SELECT_PIN_3 4
#define LEGACY_HARDWARE_SELECT_PIN_1 4
#define LEGACY_HARDWARE_SELECT_PIN_2 5
#define LEGACY_HARDWARE_SELECT_PIN_3 6
#define LEGACY_HARDWARE_SELECT_PIN_4 7
#define LEGACY_HARDWARE_SELECT_PIN_5 8
#endif

#define MODULE_LED_ONSTATE HIGH
#define MODULE_LED_OFFSTATE LOW

#else  // STM32_MODE_FLAG

#define RX5808_DATA_PIN PB3            //DATA output line to RX5808 modules
#define RX5808_CLK_PIN PB4             //CLK output line to RX5808 modules

#define RX5808_SEL0_PIN PB6            //SEL output lines to RX5808 modules
#define RX5808_SEL1_PIN PB7
#define RX5808_SEL2_PIN PB8
#define RX5808_SEL3_PIN PB9
#define RX5808_SEL4_PIN PB12
#define RX5808_SEL5_PIN PB13
#define RX5808_SEL6_PIN PB14
#define RX5808_SEL7_PIN PB15

#define BUZZER_OUTPUT_PIN PA8
#define BUZZER_OUT_ONSTATE LOW
#define BUZZER_OUT_OFFSTATE HIGH

#define AUXLED_OUTPUT_PIN PA15

#ifndef STM32_F4_PROCTYPE  // pinouts for STM32F103C8T6 "Blue Pill" module

#define RSSI_INPUT0_PIN A0             //RSSI inputs from RX5808 modules
#define RSSI_INPUT1_PIN A1
#define RSSI_INPUT2_PIN A2
#define RSSI_INPUT3_PIN A3
#define RSSI_INPUT4_PIN A4
#define RSSI_INPUT5_PIN A5
#define RSSI_INPUT6_PIN A6
#define RSSI_INPUT7_PIN A7

#define VOLTAGE_MONITOR_PIN PB1

// on the S32_BPill PCB this pin is connected to RPi GPIO24, which should be
//  configured for "heartbeat" on the RPi in "/boot/config.txt" like this:
//    dtoverlay=act-led,gpio=24
//    dtparam=act_led_trigger=heartbeat
#define RPI_SIGNAL_PIN PB0
#define RPI_SIGNAL_ONSTATE HIGH

#else                   // pinouts for STM32F411CEU6 "Black Pill" module

#define RSSI_INPUT0_PIN PB1            //RSSI inputs from RX5808 modules
#define RSSI_INPUT1_PIN A0
#define RSSI_INPUT2_PIN A1
#define RSSI_INPUT3_PIN A2
#define RSSI_INPUT4_PIN A3
#define RSSI_INPUT5_PIN A4
#define RSSI_INPUT6_PIN A5
#define RSSI_INPUT7_PIN A6

#define VOLTAGE_MONITOR_PIN PB0

#define RPI_SIGNAL_PIN A7
#define RPI_SIGNAL_ONSTATE HIGH

#endif

#define MODULE_LED_ONSTATE LOW
#define MODULE_LED_OFFSTATE HIGH

#endif  // if !STM32_MODE_FLAG

#define MODULE_LED_PIN LED_BUILTIN     // status LED on processor module

#endif  // config_h
