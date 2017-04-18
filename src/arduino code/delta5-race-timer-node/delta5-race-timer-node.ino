// Delta 5 Race Timer by Scott Chin
// SPI driver based on fs_skyrf_58g-main.c Written by Simon Chambers
// I2C functions by Mike Ochtman
// Lap trigger function by Alex Huisman
//
// MIT License
//
// Copyright (c) 2017 Scott G Chin
//
// I2C functions Mike Ochtman
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

#define rxFault 0x80
#define txFault 0x40
#define txRequest 0x20


// Node Setup -- Set the i2c address and vtx frequency
//
// Node 1 set 8, Node 2 set 10, Node 3 set 12, Node 4 set 14, Node 5 set 16, Node 6 set 18
#define i2cSlaveAddress 8
// Node 1 set 17 (5685Mhz IMD5-1), Node 2 set 25 (5760Mhz IMD5-2), Node 3 set 27 (5800Mhz IMD5-3), 
// Node 4 set 30 (5860Mhz IMD5-4), Node 5 set 21 (5905Mhz IMD5-5), Node 6 set 19 (5645Mhz IMD6-1) 
int vtxFreq = 17;


const int slaveSelectPin = 10; // Setup data pins for rx5808 comms
const int spiDataPin = 11;
const int spiClockPin = 13;

const int buttonPin = 3; // Arduino D3 as a button to set rssiTriggerThreshold, ground button to press
int buttonState = 0;

int minLapTime = 5000; // Minimum elapsed time before registering a new lap, in milliseconds
unsigned long lastLapTime = 0; // Arduino clock time that the lap started
unsigned long calcLapTime = 0; // Calculated time for the last lap
unsigned long rssiRisingTime = 0; // The time the rssi value is registered going above the threshold
unsigned long rssiFallingTime = 0; // The time the rssi value is registered going below the threshold

int rssi = 0; // Current read rssi value
int rssiTriggerThreshold = 0; // rssi threshold for detecting a quad passing the gate
int rssiTriggerBandwidth = 10; // Hysteresis for rssiTriggerThreshold

bool raceStatus = false; // True when the race has been started from the raspberry pi
bool crossing = false; // True when the quad is going through the gate

// Define data package for raspberry pi comms
struct {
	byte volatile command;
	byte volatile control; // rxFault:txFault:0:0:0:0:0:0
	byte volatile channel;
	byte volatile rssi;
	byte volatile rssiTrig;
	byte volatile lap;
	byte volatile minutes;
	byte volatile seconds;
	byte volatile milliseconds;
} commsTable;

byte volatile txTable[32];   // prepare data for sending over I2C
bool volatile dataReady = false; // flag to trigger a Serial printout after an I2C event
// use volatile for variables that will be used in interrupt service routines.
// "Volatile" instructs the compiler to get a fresh copy of the data rather than try to
// optimise temporary registers before using, as interrupts can change the value.

// Define all vtx frequencies
uint16_t vtxFreqTable[] = {
  0x2A05, 0x299B, 0x2991, 0x2987, 0x291D, 0x2913, 0x2909, 0x289F,    // Band A // add MHz references out here
  0x2903, 0x290C, 0x2916, 0x291F, 0x2989, 0x2992, 0x299C, 0x2A05,    // Band B
  0x2895, 0x288B, 0x2881, 0x2817, 0x2A0F, 0x2A19, 0x2A83, 0x2A8D,    // Band E
  0x2906, 0x2910, 0x291A, 0x2984, 0x298E, 0x2998, 0x2A02, 0x2A0C,    // Band F
  0x281D, 0x288F, 0x2902, 0x2914, 0x2987, 0x2999, 0x2A0C, 0x2A1E     // Band C / Immersion Raceband
};

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

void setup() {
	Serial.begin(9600); // For the serial monitor
	
	pinMode(buttonPin, INPUT); // Arduino physical button
	digitalWrite(buttonPin, HIGH);
	
	pinMode (slaveSelectPin, OUTPUT); // RX5808 comms
	pinMode (spiDataPin, OUTPUT);
	pinMode (spiClockPin, OUTPUT);
	digitalWrite(slaveSelectPin, HIGH);
    
	while (!Serial) {}; // Wait for the Serial port to initialise
	Serial.println("Ready");
	
	Wire.begin(i2cSlaveAddress); // I2C slave address setup
	Wire.onReceive(i2cReceive); // Register our handler function with the Wire library
	Wire.onRequest(i2cTransmit); // Register data return handler
	
	commsTable.rssiTrig = 0; // Simulate rssiTrig by adding default value
	commsTable.channel = 0; // Simulate channel by adding 0
	printCommsTable();
	setChannelModule(vtxFreq); // Set to channel defined by node setup
}

void setChannelModule(uint8_t channel) {
	uint8_t i;
	uint16_t channelData;
	
	//channelData = pgm_read_word(&vtxFreqTable[channel]);
	channelData = vtxFreqTable[channel];
  
	// bit bash out 25 bits of data
	// Order: A0-3, !R/W, D0-D19
	// A0=0, A1=0, A2=0, A3=1, RW=0, D0-19=0
	SERIAL_ENABLE_HIGH();
	delay(2);
	SERIAL_ENABLE_LOW();
	
	SERIAL_SENDBIT0();
	SERIAL_SENDBIT0();
	SERIAL_SENDBIT0();
	SERIAL_SENDBIT1();
	
	SERIAL_SENDBIT0();
	
	// remaining zeros
	for (i=20;i>0;i--)
		SERIAL_SENDBIT0();
	
	// Clock the data in
	SERIAL_ENABLE_HIGH();
	delay(2);
	SERIAL_ENABLE_LOW();
	
	// Second is the channel data from the lookup table
	// 20 bytes of register data are sent, but the MSB 4 bits are zeros
	// register address = 0x1, write, data0-15=channelData data15-19=0x0
	SERIAL_ENABLE_HIGH();
	SERIAL_ENABLE_LOW();
	
	// Register 0x1
	SERIAL_SENDBIT1();
	SERIAL_SENDBIT0();
	SERIAL_SENDBIT0();
	SERIAL_SENDBIT0();
	
	// Write to register
	SERIAL_SENDBIT1();
	
	// D0-D15
	//   note: loop runs backwards as more efficent on AVR
	for (i=16;i>0;i--) {
		// Is bit high or low?
		if (channelData & 0x1) {
			SERIAL_SENDBIT1();
		}
		else {
			SERIAL_SENDBIT0();
		}
		// Shift bits along to check the next one
		channelData >>= 1;
	}
	
	// Remaining D16-D19
	for (i=4;i>0;i--)
		SERIAL_SENDBIT0();
	
	// Finished clocking data in
	SERIAL_ENABLE_HIGH();
	delay(2);
	
	digitalWrite(slaveSelectPin,LOW); 
	digitalWrite(spiClockPin, LOW);
	digitalWrite(spiDataPin, LOW);
}

// In the future the 50pt (up to 200pt) averaging from rssiRead() should be moved here when moving averaging is in the main loop
void setRssiThreshold() {
	Serial.println(" ");
	Serial.println("Setting rssiTreshold.");
	
	int thresholdAvg = rssiRead(); // Calculate rssiThreshold average
	thresholdAvg += rssiRead();
	thresholdAvg += rssiRead();
	thresholdAvg = thresholdAvg/3; // Average of 3 rssi readings
	rssiTriggerThreshold = thresholdAvg;

	Serial.println(" ");
	Serial.print("rssiTriggerThreshold: ");
	Serial.println(rssiTriggerThreshold);
}

// Read the RSSI value for the current channel
// In the future this 50pt at a time averaging should be changing to a running average in the main loop
int rssiRead() {
	//Serial.println(" ");
	//Serial.println("Start rssiRead");
	
	int rssiAvg = 0; // Calculate rssi average
	for (uint8_t i=0; i<50; i++){
		rssiAvg += analogRead(0); // Pin A0
		//Serial.print("analogRead: ");
		//Serial.println(analogRead(0));
	}
	rssiAvg = rssiAvg/50; // Average of 50 rssi readings
	//Serial.print("rssiAvg 50pt: ");
	//Serial.println(rssiAvg);
	rssiAvg = map(rssiAvg, 1, 350, 1, 255); // Scale rssi readings from 1-350 to 1-255
	//Serial.print("rssiAvg Scaled: ");
	//Serial.println(rssiAvg);
	rssiAvg = constrain(rssiAvg, 1, 255); // Removes values below 1 and higher than 255
	//Serial.print("rssiAvg Clipped: ");
	//Serial.println(rssiAvg);

	return rssiAvg;
}

void lapCompleted() {
	float h, m, s, ms;
	unsigned long over;
		
	h = int(calcLapTime / 3600000); // Convert millis() time to h, m, s, ms
	over = calcLapTime % 3600000;
	m = int(over / 60000);
	over = over % 60000;
	s = int(over / 1000);
	over = over % 1000;
	ms = int(over/10); // Divide by 10 so that the ms never exceeds 255, i2c byte send limit
	
	commsTable.lap = commsTable.lap + 1;
	commsTable.minutes = m;
	commsTable.seconds = s;
	commsTable.milliseconds = ms;
	
	Serial.println(" ");
	Serial.print("Lap: ");
	Serial.print(commsTable.lap);
	Serial.print(" Time: ");
	Serial.print(m, 0);
	Serial.print("m ");
	Serial.print(s, 0);
	Serial.print("s ");
	Serial.print(ms, 0);
	Serial.println("ms");
}

void loop() {

	//raceStatus = true; // Uncomment for individual node testing
	//delay(500); // Uncomment for individual node testing
 
	delay(10); // Small delay for i2c comms, maybe not needed, still debugging currupt laps data
	
	rssi = rssiRead();
	commsTable.rssi = rssi;
	
	//Serial.println(" ");
	//Serial.println(" ");
	//Serial.print("Start main loop.");
	//Serial.print(" lastLapTime: ");
	//Serial.print(lastLapTime);
	//Serial.print(" calcLapTime: ");
	//Serial.print(calcLapTime);
	//Serial.print(" rssi: ");
	//Serial.print(rssi);
	//Serial.print(" rssiTriggerThreshold: ");
	//Serial.print(rssiTriggerThreshold);
	//Serial.print(" crossing: ");
	//Serial.println(crossing);
	
	if ((rssiTriggerThreshold != 0) && (millis() > (lastLapTime + minLapTime)) && (raceStatus)) { // Wait for trigger value set, elapsed minLapTime, raceStatus True
		if ((rssi > (rssiTriggerThreshold + rssiTriggerBandwidth)) && (crossing == false)) { // rssi above threshold + bandwidth and quad not already crossing
			rssiRisingTime = millis();
			Serial.print("rssiRisingTime: ");
			Serial.println(rssiRisingTime);
			crossing = true;
		}
		else if ((rssi < (rssiTriggerThreshold - rssiTriggerBandwidth)) && (crossing == true)) { // rssi below threshold - bandwidth and quad is crossing the gate
			rssiFallingTime = millis();
			Serial.print("rssiFallingTime: ");
			Serial.println(rssiFallingTime);
			crossing = false;
			
			calcLapTime = rssiRisingTime + (rssiFallingTime - rssiRisingTime)/2 - lastLapTime;

			if (lastLapTime == 0) {
				lastLapTime = rssiRisingTime + ((rssiFallingTime - rssiRisingTime)/2);
			}
			else {
				lastLapTime = rssiRisingTime + ((rssiFallingTime - rssiRisingTime)/2);
				lapCompleted();
			}
		}
	}
	
	buttonState = digitalRead(buttonPin); // Detect button press, default digital pin D3
	if (buttonState == LOW) {		
		Serial.println(" ");
		Serial.println("Button pressed.");
		setRssiThreshold();
	}
	
	if (dataReady) { // dataReady set True in i2cReceive
		printCommsTable();
		dataReady = false;
	}

	if (commsTable.control > 0) { // 
		commsTable.control = 0;
	}
}


// This function is triggered on incoming i2c data
void i2cReceive(int byteCount) {
	// if byteCount is zero, the master only checked for presence
	// of the slave device, triggering this interrupt. No response necessary
	if (byteCount == 0) return;
	
	byte command = Wire.read();
	commsTable.command = command;
	if (command < 0x80) { // commands in range 0x000-0x7F are writes TO this slave
		i2cHandleRx(command);
	} 
	else { // commands in range 0x80-0xFF are reads, requesting data FROM this device
		i2cHandleTx(command);
	}
	dataReady = true;
}

// i2cHandleRx:
// Parameters: byte, the first byte sent by the I2C master.
// returns: byte, number of bytes read, or 0xFF if error
// If the MSB of 'command' is 0, then master is sending only.
// Handle the data reception in this function.
byte i2cHandleRx(byte command) {
	// If you are here, the I2C Master has sent data
	// using one of the SMBus write commands.
	byte result = 0;
	// returns the number of bytes read, or FF if unrecognised
	// command or mismatch between data expected and received
	
	switch (command) {
		case 0x0A:  // set commsTable minutes, seconds, and milliseconds from the rasp pi
			if (Wire.available() == 3) { // good write from Master
				commsTable.minutes = Wire.read();
				commsTable.seconds = Wire.read();
				commsTable.milliseconds = Wire.read();
				result = 3;
			}
			else {
				result = 0xFF;
			}
			break;
		case 0x0B: // set commsTable lap from the rasp pi
			if (Wire.available() == 1) { // good write from Master
				commsTable.lap = Wire.read();
				result = 1;
			}
			else {
				result = 0xFF;
			}
			break;
		case 0x0C: // set rssiTriggerThreshold from the rasp pi
			if (Wire.available() == 1) { // good write from Master
				rssiTriggerThreshold = Wire.read();
				Serial.print("Command from RPi - rssiTriggerThreshold set at: ");
				Serial.println(rssiTriggerThreshold);
				result = 1;
			}
			else {
				result = 0xFF;
			}
			break;
		case 0x0D: // set minLapTime
			if (Wire.available() == 1) { // good write from Master
				minLapTime = Wire.read()*1000; // byte limit forces sending as whole seconds, convert back to ms
				result = 1;
			}
			else {
				result = 0xFF;
			}
			break;
		case 0x0E: // set raceStatus from the rasp pi
			if (Wire.available() == 1) { // good write from Master
				raceStatus = Wire.read();
				result = 1;
			}
			else {
				result = 0xFF;
			}
			break;
		case 0x0F: // set vtx frequency channel, doesn't actually change the address yet
			if (Wire.available() == 1) { // good write from Master
				vtxFreq = Wire.read();
				result = 1;
			}
			else {
				result = 0xFF;
			}
			break;
		default:
			result = 0xFF;
	}
	
	if (result == 0xFF) commsTable.control |= rxFault;
		return result;
}


// i2cHandleTx:
// Parameters: byte, the first byte sent by master
// Returns: number of bytes received, or 0xFF if error
// Used to handle SMBus process calls
byte i2cHandleTx(byte command) {
	// If you are here, the I2C Master has requested information
	
	// If there is anything we need to do before the interrupt
	// for the read takes place, this is where to do it.
	// Examples are handling process calls. Process calls do not work
	// correctly in SMBus implementation of python on linux,
	// but it may work on better implementations.
	
	// signal to i2cTransmit() that a pending command is ready
	commsTable.control |= txRequest;
	return 0;
}


// i2cTransmit:
// Parameters: none
// Returns: none
// Next function is called by twi interrupt service when twi detects
// that the Master wants to get data back from the Slave.
// Refer to Interface Specification for details of what data must be sent.
// A transmit buffer (txTable) is populated with the data before sending.

// This function is triggered on when there is outgoing data pending
void i2cTransmit() {
	byte numBytes = 0;
	int t = 0; // temporary variable used in switch occasionally below
	
	// check whether this request has a pending command.
	// if not, it was a read_byte() instruction so we should
	// return only the slave address. That is command 0.
	if ((commsTable.control & txRequest) == 0) {
		// this request did not come with a command, it is read_byte()
		commsTable.command = 0; // clear previous command
	}
	// clear the rxRequest bit; reset it for the next request
	commsTable.control &= ~txRequest;
	
	// If an invalid command is sent, we write nothing back. Master must
	// react to the crickets.
	switch (commsTable.command) {
		case 0x00: // send i2cSlaveAddress.
			txTable[0] = i2cSlaveAddress;
			numBytes = 1;
			break;
		case 0x81: // set and then send rssiTrig
			setRssiThreshold();
			commsTable.rssiTrig = rssiTriggerThreshold;
			txTable[0] = commsTable.rssiTrig;
			numBytes = 1;
			break;
		case 0x82:  // increase rssiTriggerThreshold by 5 and send
			rssiTriggerThreshold = rssiTriggerThreshold + 5;
			commsTable.rssiTrig = rssiTriggerThreshold;
			txTable[0] = commsTable.rssiTrig;
			numBytes = 1;
			break;
		case 0x83:  // decrease rssiTriggerThreshold by 5 and send
			rssiTriggerThreshold = rssiTriggerThreshold - 5;
			commsTable.rssiTrig = rssiTriggerThreshold;
			txTable[0] = commsTable.rssiTrig;
			numBytes = 1;
			break;
		case 0x90: // send current lap number and lap time as an array
			txTable[0] = commsTable.lap;
			txTable[1] = commsTable.minutes;
			txTable[2] = commsTable.seconds;
			txTable[3] = commsTable.milliseconds;
			numBytes = 4;
			break;
		case 0x91: // send minutes channel // when is this needed???
			txTable[0] = commsTable.minutes;
			numBytes = 1;
			break;
		case 0x92: // send seconds channel // when is this needed???
			txTable[0] = commsTable.seconds;
			numBytes = 1;
			break;
		case 0x93: // send milliseconds channel // when is this needed???
			txTable[0] = commsTable.milliseconds;
			numBytes = 1;
			break;
		case 0xA0: // send rssi
			txTable[0] = commsTable.rssi;
			numBytes = 1;
			break;		
		default:
			// If an invalid command is sent, we write nothing back. Master must
			// react to the sound of crickets.
			commsTable.control |= txFault;
	}
	if (numBytes > 0) {
		Wire.write((byte *)&txTable, numBytes);
	}
}


// Prints to arduino serial console for debugging
void printCommsTable() {
	String builder = "";
	builder = "commsTable contents:";
	Serial.println(builder);
	builder = "  Command: ";
	builder += String(commsTable.command, HEX);
	Serial.println(builder);
	builder = "  Control: ";
	builder += String(commsTable.control, HEX);
	Serial.println(builder);
	builder = "  Channel: ";
	builder += commsTable.channel;
	Serial.println(builder);
	builder = "  RSSI: ";
	builder += commsTable.rssi;
	Serial.println(builder);
	builder = "  RSSI Triger: ";
	builder += commsTable.rssiTrig;
	Serial.println(builder);
	builder = "  Lap: ";
	builder += commsTable.lap;
	Serial.println(builder);
	builder = "  Minutes: ";
	builder += commsTable.minutes;
	Serial.println(builder);
	builder = "  Seconds: ";
	builder += commsTable.seconds;
	Serial.println(builder);
	builder = "  Milliseconds: ";
	builder += commsTable.milliseconds;
	Serial.println(builder);
	Serial.println();
}

// Not currently called anywhere
void printTxTable() {
	Serial.println("Transmit Table");
	for (byte i = 0; i < 32; i++) {
		Serial.print("  ");
		Serial.print(i);
		Serial.print(": ");
		Serial.println(txTable[i]);
	}
	Serial.println();
}

