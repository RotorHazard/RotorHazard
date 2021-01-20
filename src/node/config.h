#ifndef config_h
#define config_h

#include "util/rhtypes.h"

// ******************************************************************** //

// *** Node Setup - Set node number here (1-8): ***
#define NODE_NUMBER 0

// Set to 1-8 for manual selection.

// Set to 0 for automatic selection via hardware pin.
// See https://github.com/RotorHazard/RotorHazard/wiki/Specification:-Node-hardware-addressing

// ******************************************************************** //

#define SERIAL_BAUD_RATE 115200

#include <Arduino.h>

#if defined(__TEST__)
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
#elif defined(__TEST__)
#define RX5808_DATA_PIN 0             //DATA output line to RX5808 module
#define RX5808_SEL_PIN 0              //CLK output line to RX5808 module
#define RX5808_CLK_PIN 0              //SEL output line to RX5808 module
#define RSSI_INPUT_PIN 0              //RSSI input from RX5808
#define NODE_RESET_PIN 0              //Pin to reset paired Arduino via command for ISP
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

#define MULTI_RHNODE_MAX 1
#define READS_PER_FREQ 256

#endif  // config_h
