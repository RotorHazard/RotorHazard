// Delta 5 Race Timer by Scott Chin
// SPI driver based on fs_skyrf_58g-main.c Written by Simon Chambers
// I2C functions by Mike Ochtman
// Lap trigger function by Alex Huisman
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

#define rxFault 0x80
#define txFault 0x40
#define txRequest 0x20


// Node Setup -- Set the i2c address and vtx frequency
//
// Node 1 set 8, Node 2 set 10, Node 3 set 12, Node 4 set 14, Node 5 set 16, Node 6 set 18
#define i2cSlaveAddress 8
// Node 1 set 17 (5685Mhz IMD5-1), Node 2 set 25 (5760Mhz IMD5-2), Node 3 set 27 (5800Mhz IMD5-3), 
// Node 4 set 30 (5860Mhz IMD5-4), Node 5 set 21 (5905Mhz IMD5-5), Node 6 set 19 (5645Mhz IMD6-1) 
int vtxFreq = 17; // This should be set from the pi config // rename vtxNum to match webinterface, move to commsTable?


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

int rssi = 0; // Current read rssi value // move to commsTable?
int rssiTriggerThreshold = 0; // rssi threshold for detecting a quad passing the gate // move to commsTable?
int rssiTriggerBandwidth = 10; // Hysteresis for rssiTriggerThreshold

bool raceStatus = false; // True when the race has been started from the raspberry pi
bool crossing = false; // True when the quad is going through the gate

// Define data package for raspberry pi comms
// Should all duplicate variables be just used in the comms table?
struct {
	byte volatile command;
	byte volatile control; // rxFault:txFault:0:0:0:0:0:0
	byte volatile channel; // rename vtxNum to match web interface
	byte volatile rssi;
	byte volatile rssiTrig;
	byte volatile lap;
	byte volatile minutes;
	byte volatile seconds;
	byte volatile milliseconds;
} commsTable;

byte volatile txTable[32]; // prepare data for sending over I2C
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
	Serial.begin(115200); // start serial for output
	
	pinMode(buttonPin, INPUT); // Define digital button for setting rssi trigger
	digitalWrite(buttonPin, HIGH);
	
	pinMode (slaveSelectPin, OUTPUT); // RX5808 comms
	pinMode (spiDataPin, OUTPUT);
	pinMode (spiClockPin, OUTPUT);
	digitalWrite(slaveSelectPin, HIGH);
    
	while (!Serial) {}; // Wait for the Serial port to initialise
	Serial.println("Ready");
	
	Wire.begin(i2cSlaveAddress); // I2C slave address setup
	Wire.onReceive(i2cReceive); // Trigger 'i2cReceive' function on incoming data
	Wire.onRequest(i2cTransmit); // Trigger 'i2cTransmit' function for outgoing data
	
	// Initialize commsTable
	commsTable.channel = vtxFreq;
	commsTable.rssi = 0;
	commsTable.rssiTrig = 0;
	commsTable.lap = 0;
	commsTable.minutes = 0;
	commsTable.seconds = 0;
	commsTable.milliseconds = 0;
	
	printCommsTable(); // this isnt needed
		
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
// This function should only exist for thriggering from a button on the arduino, the pi should send the trigger value normally
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
	//delay(500);
 	
	rssi = rssiRead();
	
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
			
			calcLapTime = rssiRisingTime + (rssiFallingTime - rssiRisingTime)/2 - lastLapTime; // Calculates the completed lap time

			if (lastLapTime == 0) { // Race starting, this logs the first time through the gate
				lastLapTime = rssiRisingTime + ((rssiFallingTime - rssiRisingTime)/2); // Sets the arduino clock time through the gate
				Serial.print("Fly over start!");
			}
			else { // Race is running, this is a lap completed
				lastLapTime = rssiRisingTime + ((rssiFallingTime - rssiRisingTime)/2); // Sets the arduino clock time through the gate
				lapCompleted();
			}
		}
	}
	
	buttonState = digitalRead(buttonPin); // Detect button press to set rssi trigger
	if (buttonState == LOW) {		
		Serial.println(" ");
		Serial.println("Button pressed.");
		setRssiThreshold();
	}
	
	printCommsTable(); // Testing only
	printTxTable();	// Testing only
	
	if (dataReady) { // Set True in i2cReceive, check to print current commsTable
		printCommsTable();
		//printTxTable(); // Testing only
		dataReady = false;
	}
	
	
	if (commsTable.control > 0) { // 
		printTxTable();
		commsTable.control = 0;
	}
}


// Function called by twi interrupt service when master sends information to the slave
// or when master sets up a specific read request
void i2cReceive(int byteCount) { // Number of bytes in rx buffer
	// If byteCount is zero, the master only checked for presence of the slave device
	// triggering this interrupt, no response necessary
	if (byteCount == 0) return;
	
	byte command = Wire.read(); // The first byte sent is a command byte
	commsTable.command = command;
	
	if (command < 0x80) { // Commands in range 0x00-0x7F are writes TO this device
		i2cHandleRx(command);
	} 
	else { // Commands in range 0x80-0xFF are requests FROM this device
		i2cHandleTx(command);
	}
	dataReady = true; // Flag to the main loop to print the commsTable
}

// Function called by i2cReceive for writes TO this device, the I2C Master has sent data
// using one of the SMBus write commands, if the MSB of 'command' is 0, master is sending only
// Returns the number of bytes read, or FF if unrecognised command or mismatch between
// data expected and received
byte i2cHandleRx(byte command) { // The first byte sent by the I2C master is the command
	byte result = 0; // Initialize result variable
	
	switch (command) {
		case 0x0A: // Main reset, set lap, min, sec, ms to zero, lastLapTime to 0, raceStatus to 0, receive minLapTime and vtx frequency
			if (Wire.available() == 2) { // Confirm expected number of bytes
				commsTable.lap = 0;
				lastLapTime = 0;
				commsTable.minutes = 0;
				commsTable.seconds = 0;
				commsTable.milliseconds = 0;
				commsTable.rssiTrig = 0;
				minLapTime = Wire.read()*1000; // Byte limit forces sending as whole seconds, convert back to ms
				raceStatus = 0;
				vtxFreq = Wire.read();
				commsTable.channel = vtxFreq;
				//Serial.print("Command from RPi - Main reset."); // No serial prints in Interrupt Service Routine
				//Serial.println(minLapTime);
				//Serial.println(vtxFreq);
				result = 2;
			}
			else {
				result = 0xFF;
			}
			break;
		case 0x0B: // Race starting reset, set lap, min, sec, ms, lastLapTime to 0, raceStatus to 1, receives lap number (0)
			if (Wire.available() == 1) { // Confirm expected number of bytes
				commsTable.lap = Wire.read(); // Reads one byte, rework function to not need to read anything
				commsTable.lap = 0;
				lastLapTime = 0; // Reset to zero to catch first gate fly through again
				commsTable.minutes = 0;
				commsTable.seconds = 0;
				commsTable.milliseconds = 0;
				raceStatus = 1;
				//Serial.print("Command from RPi - Race reset.");  // No serial prints in Interrupt Service Routine
				result = 1;
			}
			else {
				result = 0xFF;
			}
			break;
		case 0x0C: // Set rssiTriggerThreshold from the rasp pi
			if (Wire.available() == 1) { // Confirm expected number of bytes
				rssiTriggerThreshold = Wire.read();
				commsTable.rssiTrig = rssiTriggerThreshold;
				//Serial.print("Command from RPi - rssiTriggerThreshold set at: "); // No serial prints in Interrupt Service Routine
				//Serial.println(rssiTriggerThreshold);
				result = 1;
			}
			else {
				result = 0xFF;
			}
			break;
		case 0x0D: // set minLapTime
			if (Wire.available() == 1) { // Confirm expected number of bytes
				minLapTime = Wire.read()*1000; // Byte limit forces sending as whole seconds, convert back to ms
				//Serial.print("Command from RPi - minLapTime set at: "); // No serial prints in Interrupt Service Routine
				//Serial.println(minLapTime);
				result = 1;
			}
			else {
				result = 0xFF;
			}
			break;
		case 0x0E: // Set raceStatus from the rasp pi
			if (Wire.available() == 1) { // Confirm expected number of bytes
				raceStatus = Wire.read();
				//Serial.print("Command from RPi - raceStatus set at: "); // No serial prints in Interrupt Service Routine
				//Serial.println(raceStatus);
				result = 1;
			}
			else {
				result = 0xFF;
			}
			break;
		case 0x0F: // Set vtx frequency channel
			if (Wire.available() == 1) { // Confirm expected number of bytes
				vtxFreq = Wire.read();
				commsTable.channel = vtxFreq;
				setChannelModule(vtxFreq); // Shouldn't do this in Interrupt Service Routine
				//Serial.print("Command from RPi - vtxFreq set at: "); // No serial prints in Interrupt Service Routine
				//Serial.println(vtxFreq);
				result = 1;
			}
			else {
				result = 0xFF;
			}
			break;
		default: // If no case matches return FF for fault
			result = 0xFF;
	}
	
	if (result == 0xFF) {
		commsTable.control |= rxFault; // Set control to rxFault if FF result
		
		// Fix option for i2c failure, try restarting wire
		//Wire.begin(i2cSlaveAddress); // Restart i2c
		//Wire.onReceive(i2cReceive); // Trigger 'i2cReceive' function on incoming data
		//Wire.onRequest(i2cTransmit); // Trigger 'i2cTransmit' function for outgoing data
		
		// Fix option for i2c failure, try reading extra bytes
		int garbage = 1;
		while(Wire.available()) garbage = Wire.read();
	}
	return result;
}

// Function called by i2cReceive for reads FROM this device, the I2C Master requests data
// Returns the number of bytes received, or 0xFF if error
// Used to handle SMBus process calls
byte i2cHandleTx(byte command) { // The first byte sent by the I2C master is the command
	// signal to i2cTransmit function that a pending command is ready
	commsTable.control |= txRequest;
	return 0;
}

// Function called by twi interrupt service when the Master wants to get data from the Slave
// No parameters and no returns
// A transmit buffer (txTable) is populated with the data before sending.
void i2cTransmit() {
	byte numBytes = 0; // Initialize numBytes variable
	int t = 0; // Temporary variable used in switch occasionally below
	
	// Check whether this request has a pending command, if not, it was a read_byte()
	// instruction so we should return only the slave address, that is command 0
	if ((commsTable.control & txRequest) == 0) {
		// This request did not come with a command, it is read_byte()
		commsTable.command = 0; // Clear previous command
	}
	// Clear the rxRequest bit, resetting it for the next request
	commsTable.control &= ~txRequest;
	
	switch (commsTable.command) {
		case 0x00: // Send i2cSlaveAddress.
			txTable[0] = i2cSlaveAddress;
			numBytes = 1;
			break;
		case 0x81: // Set and then send rssiTrig // the pi should just tell the arduino what the trigger is based on the current known rssi
			setRssiThreshold(); // shouldn't do this in Interrupt Service Routine
			commsTable.rssiTrig = rssiTriggerThreshold;
			txTable[0] = commsTable.rssiTrig;
			numBytes = 1;
			break;
		case 0x82:  // Increase rssiTriggerThreshold by 5 and send
			rssiTriggerThreshold = rssiTriggerThreshold + 5;
			commsTable.rssiTrig = rssiTriggerThreshold;
			txTable[0] = commsTable.rssiTrig;
			numBytes = 1;
			break;
		case 0x83:  // Decrease rssiTriggerThreshold by 5 and send
			rssiTriggerThreshold = rssiTriggerThreshold - 5;
			commsTable.rssiTrig = rssiTriggerThreshold;
			txTable[0] = commsTable.rssiTrig;
			numBytes = 1;
			break;
		case 0x90: // Main comms loop request, send rssi, lap number, and lap time as an array
			commsTable.rssi = rssi;
			txTable[0] = commsTable.rssi;
			txTable[1] = commsTable.lap;
			txTable[2] = commsTable.minutes;
			txTable[3] = commsTable.seconds;
			txTable[4] = commsTable.milliseconds;
			numBytes = 5;
			break;
		case 0x91: // Send minutes channel // This is not needed, remove
			txTable[0] = commsTable.minutes;
			numBytes = 1;
			break;
		case 0x92: // Send seconds channel // This is not needed, remove
			txTable[0] = commsTable.seconds;
			numBytes = 1;
			break;
		case 0x93: // Send milliseconds channel // This is not needed, remove
			txTable[0] = commsTable.milliseconds;
			numBytes = 1;
			break;	
		default:
			// If an invalid command is sent, write nothing back, master must react to
			// the sound of crickets
			commsTable.control |= txFault;
	}
	if (numBytes > 0) { // If there is pending data, send it
		Wire.write((byte *)&txTable, numBytes);
	}
}

// Prints to commsTable to arduino serial console
// Are all these builder lines needed?
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

// Prints to transmit buffer to arduino serial console
void printTxTable() {
	Serial.println("Transmit Table:");
	for (byte i = 0; i < 32; i++) {
		Serial.print(" ");
		//Serial.print(i); // Minimize by only showing data
		//Serial.print(":");
		Serial.print(txTable[i]);
	}
	Serial.println();
}

