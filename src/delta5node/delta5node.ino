// Delta 5 Race Timer by Scott Chin
// SPI driver based on fs_skyrf_58g-main.c Written by Simon Chambers
// I2C functions by Mike Ochtman
//
// MIT License
//
// Copyright (c) 2017 Scott G Chin
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

// Node Setup -- Set the i2c address here
// Node 1 = 8, Node 2 = 10, Node 3 = 12, Node 4 = 14
// Node 5 = 16, Node 6 = 18, Node 7 = 20, Node 8 = 22
#define i2cSlaveAddress 8

const int slaveSelectPin = 10; // Setup data pins for rx5808 comms
const int spiDataPin = 11;
const int spiClockPin = 13;

#define READ_ADDRESS 0x00
#define READ_FREQUENCY 0x03
#define READ_LAP_STATS 0x05
#define READ_CALIBRATION_THRESHOLD 0x15
#define READ_CALIBRATION_MODE 0x16
#define READ_CALIBRATION_OFFSET 0x17
#define READ_TRIGGER_THRESHOLD 0x18
#define READ_FILTER_RATIO 0x19

#define WRITE_FREQUENCY 0x51
#define WRITE_CALIBRATION_THRESHOLD 0x65
#define WRITE_CALIBRATION_MODE 0x66
#define WRITE_CALIBRATION_OFFSET 0x67
#define WRITE_TRIGGER_THRESHOLD 0x68
#define WRITE_FILTER_RATIO 0x69

struct {
	uint16_t volatile vtxFreq = 5800;
	// Subtracted from the peak rssi during a calibration pass to determine the trigger value
	uint16_t volatile calibrationOffset = 8;
	// Rssi must fall below trigger - settings.calibrationThreshold to end a calibration pass
	uint16_t volatile calibrationThreshold = 95;
	// Rssi must fall below trigger - settings.triggerThreshold to end a normal pass
	uint16_t volatile triggerThreshold = 40;
	uint8_t volatile filterRatio = 10;
	float volatile filterRatioFloat = 0.0f;
} settings;

struct {
	bool volatile calibrationMode = false;
	// True when the quad is going through the gate
	bool volatile crossing = false;
	// Current unsmoothed rssi
	uint16_t volatile rssiRaw = 0;
	// Smoothed rssi value, needs to be a float for smoothing to work
	float volatile rssiSmoothed = 0;
	// int representation of the smoothed rssi value
	uint16_t volatile rssi = 0;
	// rssi value that will trigger a new pass
	uint16_t volatile rssiTrigger;
	// The peak raw rssi seen the current pass
	uint16_t volatile rssiPeakRaw = 0;
	// The peak smoothed rssi seen the current pass
	uint16_t volatile rssiPeak = 0;
	// The time of the peak raw rssi for the current pass
	uint32_t volatile rssiPeakRawTimeStamp = 0;

	// variables to track the loop time
	uint32_t volatile loopTime = 0;
	uint32_t volatile lastLoopTimeStamp = 0;
} state;

struct {
	uint16_t volatile rssiPeakRaw;
	uint16_t volatile rssiPeak;
	uint32_t volatile timeStamp;
	uint8_t volatile lap;
} lastPass;

uint8_t volatile ioCommand; // I2C code to identify messages
uint8_t volatile ioBuffer[32]; // Data array for sending over i2c, up to 32 bytes per message
int ioBufferSize = 0;
int ioBufferIndex = 0;

// Defines for fast ADC reads
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))

// Initialize program
void setup() {
	Serial.begin(115200); // Start serial for output/debugging

	pinMode (slaveSelectPin, OUTPUT); // RX5808 comms
	pinMode (spiDataPin, OUTPUT);
	pinMode (spiClockPin, OUTPUT);
	digitalWrite(slaveSelectPin, HIGH);

	while (!Serial) {
	}; // Wait for the Serial port to initialise
	Serial.print("Ready: ");
	Serial.println(i2cSlaveAddress);

	Wire.begin(i2cSlaveAddress); // I2C slave address setup
	Wire.onReceive(i2cReceive); // Trigger 'i2cReceive' function on incoming data
	Wire.onRequest(i2cTransmit); // Trigger 'i2cTransmit' function for outgoing data, on master request

	// set ADC prescaler to 16 to speedup ADC readings
    sbi(ADCSRA,ADPS2);
    cbi(ADCSRA,ADPS1);
    cbi(ADCSRA,ADPS0);

	// Initialize lastPass defaults
	settings.filterRatioFloat = settings.filterRatio / 1000.0f;
	state.rssi = 0;
	state.rssiTrigger = 0;
	lastPass.rssiPeakRaw = 0;
	lastPass.rssiPeak = 0;
	lastPass.lap = 0;
	lastPass.timeStamp = 0;

	setRxModule(settings.vtxFreq); // Setup rx module to default frequency
}

// Functions for the rx5808 module
void SERIAL_SENDBIT1() {
	digitalWrite(spiClockPin, LOW);
	delayMicroseconds(300);
	digitalWrite(spiDataPin, HIGH);
	delayMicroseconds(300);
	digitalWrite(spiClockPin, HIGH);
	delayMicroseconds(300);
	digitalWrite(spiClockPin, LOW);
	delayMicroseconds(300);
}
void SERIAL_SENDBIT0() {
	digitalWrite(spiClockPin, LOW);
	delayMicroseconds(300);
	digitalWrite(spiDataPin, LOW);
	delayMicroseconds(300);
	digitalWrite(spiClockPin, HIGH);
	delayMicroseconds(300);
	digitalWrite(spiClockPin, LOW);
	delayMicroseconds(300);
}
void SERIAL_ENABLE_LOW() {
	delayMicroseconds(100);
	digitalWrite(slaveSelectPin,LOW);
	delayMicroseconds(100);
}
void SERIAL_ENABLE_HIGH() {
	delayMicroseconds(100);
	digitalWrite(slaveSelectPin,HIGH);
	delayMicroseconds(100);
}

// Calculate rx5808 register hex value for given frequency in MHz
uint16_t freqMhzToRegVal(uint16_t freqInMhz) {
  uint16_t tf, N, A;
  tf = (freqInMhz - 479) / 2;
  N = tf / 32;
  A = tf % 32;
  return (N<<7) + A;
}

// Set the frequency given on the rx5808 module
void setRxModule(int frequency) {
	uint8_t i; // Used in the for loops

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

	for (i = 20; i > 0; i--) SERIAL_SENDBIT0(); // Remaining zeros

	SERIAL_ENABLE_HIGH(); // Clock the data in
	delay(2);
	SERIAL_ENABLE_LOW();

	// Second is the channel data from the lookup table, 20 bytes of register data are sent, but the
	// MSB 4 bits are zeros register address = 0x1, write, data0-15=vtxHex data15-19=0x0
	SERIAL_ENABLE_HIGH();
	SERIAL_ENABLE_LOW();

	SERIAL_SENDBIT1(); // Register 0x1
	SERIAL_SENDBIT0();
	SERIAL_SENDBIT0();
	SERIAL_SENDBIT0();

	SERIAL_SENDBIT1(); // Write to register

	// D0-D15, note: loop runs backwards as more efficent on AVR
	for (i = 16; i > 0; i--) {
		if (vtxHex & 0x1) { // Is bit high or low?
			SERIAL_SENDBIT1();
		}
		else {
			SERIAL_SENDBIT0();
		}
		vtxHex >>= 1; // Shift bits along to check the next one
	}

	for (i = 4; i > 0; i--) // Remaining D16-D19
		SERIAL_SENDBIT0();

	SERIAL_ENABLE_HIGH(); // Finished clocking data in
	delay(2);

	digitalWrite(slaveSelectPin,LOW);
	digitalWrite(spiClockPin, LOW);
	digitalWrite(spiDataPin, LOW);
}


// Read the RSSI value for the current channel
int rssiRead() {
	return analogRead(0);
}

// Main loop
void loop() {
	//delay(250);

	// Calculate the time it takes to run the main loop
	uint32_t lastLoopTimeStamp = state.lastLoopTimeStamp;
	state.lastLoopTimeStamp = micros();
	state.loopTime = state.lastLoopTimeStamp - lastLoopTimeStamp;

	state.rssiRaw = rssiRead();
	state.rssiSmoothed = (settings.filterRatioFloat * (float)state.rssiRaw) + ((1.0f-settings.filterRatioFloat) * state.rssiSmoothed);
	state.rssi = (int)state.rssiSmoothed;

	if (state.rssiTrigger > 0) {
		if (!state.crossing && state.rssi > state.rssiTrigger) {
			state.crossing = true; // Quad is going through the gate
			Serial.println("Crossing = True");
		}

		// Find the peak rssi and the time it occured during a crossing event
		// Use the raw value to account for the delay in smoothing.
		if (state.rssiRaw > state.rssiPeakRaw) {
			state.rssiPeakRaw = state.rssiRaw;
			state.rssiPeakRawTimeStamp = millis();
		}

		if (state.crossing) {
			int triggerThreshold = settings.triggerThreshold;

			// If in calibration mode, keep raising the trigger value
			if (state.calibrationMode) {
				state.rssiTrigger = max(state.rssiTrigger, state.rssi - settings.calibrationOffset);
				// when calibrating, use a larger threshold
				triggerThreshold = settings.calibrationThreshold;
			}

			state.rssiPeak = max(state.rssiPeak, state.rssi);

			// Make sure the threshold does not put the trigger below 0 RSSI
			// See if we have left the gate
			if ((state.rssiTrigger > triggerThreshold) &&
				(state.rssi < (state.rssiTrigger - triggerThreshold))) {
				Serial.println("Crossing = False");
				lastPass.rssiPeakRaw = state.rssiPeakRaw;
				lastPass.rssiPeak = state.rssiPeak;
				lastPass.timeStamp = state.rssiPeakRawTimeStamp;
				lastPass.lap = lastPass.lap + 1;

				state.crossing = false;
				state.calibrationMode = false;
				state.rssiPeakRaw = 0;
				state.rssiPeak = 0;
			}
		}
	}
}


// Function called by twi interrupt service when master sends information to the slave
// or when master sets up a specific read request
void i2cReceive(int byteCount) { // Number of bytes in rx buffer
	// If byteCount is zero, the master only checked for presence of the slave device, no response necessary
	if (byteCount == 0) {
		Serial.println("Error: no bytes for a receive?");
		return;
	}

	if (byteCount != Wire.available()) {
		Serial.println("Error: rx byte count and wire available don't agree");
	}

	ioCommand = Wire.read(); // The first byte sent is a command byte

	if (ioCommand > 0x50) { // Commands > 0x50 are writes TO this slave
		i2cHandleRx(ioCommand);
	}
	else { // Otherwise this is a request FROM this device
		if (Wire.available()) { // There shouldn't be any data present on the line for a read request
			Serial.print("Error: Wire.available() on a read request.");
			Serial.println(ioCommand, HEX);
			while(Wire.available()) {
				Wire.read();
			}
		}
	}
}

bool readAndValidateIoBuffer(byte command, int expectedSize) {
	uint8_t checksum = 0;
	ioBufferSize = 0;
	ioBufferIndex = 0;

	if (expectedSize == 0) {
		Serial.println("No Expected Size");
		return true;
	}

	if (!Wire.available()) {
		Serial.println("Nothing Avialable");
		return false;
	}

	while(Wire.available()) {
		ioBuffer[ioBufferSize++] = Wire.read();
		if (expectedSize + 1 < ioBufferSize) {
			checksum += ioBuffer[ioBufferSize-1];
		}
	}

	if (checksum != ioBuffer[ioBufferSize-1] ||
		ioBufferSize-2 != expectedSize) {
		Serial.println("invalid checksum");
		Serial.println(checksum);
		Serial.println(ioBuffer[ioBufferSize-1]);
		Serial.println(ioBufferSize-2);
		Serial.println(expectedSize);
		return false;
	}

	if (command != ioBuffer[ioBufferSize-2]) {
		Serial.println("command does not match");
		return false;
	}
	return true;
}

uint8_t ioBufferRead8() {
	return ioBuffer[ioBufferIndex++];
}

uint16_t ioBufferRead16() {
	uint16_t result;
	result = ioBuffer[ioBufferIndex++];
	result = (result << 8) | ioBuffer[ioBufferIndex++];
	return result;
}

void ioBufferWrite8(uint8_t data) {
	ioBuffer[ioBufferSize++] = data;
}

void ioBufferWrite16(uint16_t data) {
	ioBuffer[ioBufferSize++] = (uint16_t)(data >> 8);
	ioBuffer[ioBufferSize++] = (uint16_t)(data & 0xFF);
}

void ioBufferWrite32(uint32_t data) {
	ioBuffer[ioBufferSize++] = (uint16_t)(data >> 24);
	ioBuffer[ioBufferSize++] = (uint16_t)(data >> 16);
	ioBuffer[ioBufferSize++] = (uint16_t)(data >> 8);
	ioBuffer[ioBufferSize++] = (uint16_t)(data & 0xFF);
}

void ioBufferWriteChecksum() {
	uint8_t checksum = 0;
	for (int i = 0; i < ioBufferSize ; i++) {
		checksum += ioBuffer[i];
	}

	ioBufferWrite8(checksum);
}

// Function called by i2cReceive for writes TO this device, the I2C Master has sent data
// using one of the SMBus write commands, if the MSB of 'command' is 0, master is sending only
// Returns the number of bytes read, or FF if unrecognised command or mismatch between
// data expected and received
byte i2cHandleRx(byte command) { // The first byte sent by the I2C master is the command
	bool success = false;

	switch (command) {
		case WRITE_FREQUENCY:
			if (readAndValidateIoBuffer(0x51, 2)) {
				settings.vtxFreq = ioBufferRead16();
				setRxModule(settings.vtxFreq); // Shouldn't do this in Interrupt Service Routine
				success = true;
			}
			break;
		case WRITE_CALIBRATION_THRESHOLD:
			if (readAndValidateIoBuffer(WRITE_CALIBRATION_THRESHOLD, 2)) {
				settings.calibrationThreshold = ioBufferRead16();
				success = true;
			}
			break;
		case WRITE_CALIBRATION_MODE:
			if (readAndValidateIoBuffer(WRITE_CALIBRATION_MODE, 1)) {
				state.calibrationMode = ioBufferRead8();
				state.rssiTrigger = state.rssi - settings.calibrationOffset;
				lastPass.rssiPeakRaw = 0;
				lastPass.rssiPeak = 0;
				state.rssiPeakRaw = 0;
				state.rssiPeakRawTimeStamp = 0;
				success = true;
			}
			break;
		case WRITE_CALIBRATION_OFFSET:
			if (readAndValidateIoBuffer(WRITE_CALIBRATION_OFFSET, 2)) {
				settings.calibrationOffset = ioBufferRead16();
				success = true;
			}
			break;
		case WRITE_TRIGGER_THRESHOLD:
			if (readAndValidateIoBuffer(WRITE_TRIGGER_THRESHOLD, 2)) {
				settings.triggerThreshold = ioBufferRead16();
				success = true;
			}
			break;
		case WRITE_FILTER_RATIO:
			if (readAndValidateIoBuffer(WRITE_FILTER_RATIO, 1)) {
				settings.filterRatio = ioBufferRead8();
				settings.filterRatioFloat =  settings.filterRatio / 1000.0f;
				success = true;
			}
			break;
	}

	ioCommand = 0; // Clear previous command

	if (!success) { // Set control to rxFault if 0xFF result
		 Serial.print("RX Fault command: ");
		 Serial.println(command, HEX);
	}
	return success;
}

// Function called by twi interrupt service when the Master wants to get data from the Slave
// No parameters and no returns
// A transmit buffer (ioBuffer) is populated with the data before sending.
void i2cTransmit() {
	ioBufferSize = 0;

	switch (ioCommand) {
		case READ_ADDRESS:
			ioBufferWrite8(i2cSlaveAddress);
			break;
		case READ_FREQUENCY:
			ioBufferWrite16(settings.vtxFreq);
			break;
		case READ_LAP_STATS:
			ioBufferWrite8(lastPass.lap);
			ioBufferWrite32(millis() - lastPass.timeStamp);
			ioBufferWrite16(state.rssi);
			ioBufferWrite16(state.rssiTrigger);
			ioBufferWrite16(lastPass.rssiPeakRaw);
			ioBufferWrite16(lastPass.rssiPeak);
			ioBufferWrite32(state.loopTime);
			break;
		case READ_CALIBRATION_THRESHOLD:
			ioBufferWrite16(settings.calibrationThreshold);
			break;
		case READ_CALIBRATION_MODE:
			ioBufferWrite8(state.calibrationMode);
			break;
		case READ_CALIBRATION_OFFSET:
			ioBufferWrite16(settings.calibrationOffset);
			break;
		case READ_TRIGGER_THRESHOLD:
			ioBufferWrite16(settings.triggerThreshold);
			break;
		case READ_FILTER_RATIO:
			ioBufferWrite8(settings.filterRatio);
			break;
		default: // If an invalid command is sent, write nothing back, master must react
			Serial.print("TX Fault command: ");
			Serial.println(ioCommand, HEX);
	}

	ioCommand = 0; // Clear previous command

	if (ioBufferSize > 0) { // If there is pending data, send it
		ioBufferWriteChecksum();
		Wire.write((byte *)&ioBuffer, ioBufferSize);
	}
}
