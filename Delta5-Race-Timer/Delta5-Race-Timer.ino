//Delta 5 Race Timer by Scott Chin Version 0.2
//SPI driver based on fs_skyrf_58g-main.c Written by Simon Chambers
//I2C functions by Mike Ochtman
//Lap trigger function by Andrey Voroshkov

//MIT License
//
//Copyright (c) 2017 Scott G Chin
//
//I2C functions Mike Ochtman
//
//Permission is hereby granted, free of charge, to any person obtaining a copy
//of this software and associated documentation files (the "Software"), to deal
//in the Software without restriction, including without limitation the rights
//to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
//copies of the Software, and to permit persons to whom the Software is
//furnished to do so, subject to the following conditions:
//
//The above copyright notice and this permission notice shall be included in all
//copies or substantial portions of the Software.
//
//THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
//IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
//FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
//AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
//LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
//OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
//SOFTWARE.

#include <Wire.h>

#define rxFault 0x80
#define txFault 0x40
#define txRequest 0x20

// ************Set the slave address and the channel *************************

#define slaveAddress 18 //i2c address to Raspberry Pi. 8-1, 10-2, 12-3, 14-4, 16-5, 18-6
int count = 19; //channel 5685-17, 5760-25, 5800-27, 5860-30, 5905-21,5645-19

// ***************************************************************************

const int slaveSelectPin = 10;
const int spiDataPin = 11;
const int spiClockPin = 13;
const int buttonPin = 3; 
int buttonState = 0;  
int downcount=0;
int rssi = 0;
int highValue=0;
int highChannel=0;
unsigned long start, finished, elapsed, lapcheck;
int flag = 0;
int lapTrigger = 0; //default RSSI threshold for good lap
int minLap = 5000; // Minimum lap time in milliseconds

uint16_t rssiArr[6];
uint16_t rssiThreshold = 0;
#define MAGIC_THRESHOLD_REDUCE_CONSTANT 2
#define THRESHOLD_ARRAY_SIZE 100
uint16_t rssiThresholdArray[THRESHOLD_ARRAY_SIZE];

struct {
  byte volatile command;
  byte volatile control; // rxFault:txFault:0:0:0:0:0:0
  byte volatile rssiTrig;
  byte volatile channel;
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

//PROGMEM prog_uint16_t channelTable[] = {
uint16_t channelTable[] = {
  0x2A05, 0x299B, 0x2991, 0x2987, 0x291D, 0x2913, 0x2909, 0x289F,    //Band A
  0x2903, 0x290C, 0x2916, 0x291F, 0x2989, 0x2992, 0x299C, 0x2A05,    //Band B
  0x2895, 0x288B, 0x2881, 0x2817, 0x2A0F, 0x2A19, 0x2A83, 0x2A8D,    //Band E
  0x2906, 0x2910, 0x291A, 0x2984, 0x298E, 0x2998, 0x2A02, 0x2A0C,    //Band F
  0x281D, 0x288F, 0x2902, 0x2914, 0x2987, 0x2999, 0x2A0C, 0x2A1E     // Band C / Immersion Raceband
};

void SERIAL_SENDBIT1()
{
  digitalWrite(spiClockPin, LOW);
  delayMicroseconds(300);
  
digitalWrite(spiDataPin, HIGH);
  delayMicroseconds(300);
  digitalWrite(spiClockPin, HIGH);
  delayMicroseconds(300);
  
  digitalWrite(spiClockPin, LOW);
  delayMicroseconds(300);
}

void SERIAL_SENDBIT0()
{
  digitalWrite(spiClockPin, LOW);
  delayMicroseconds(300);
  
digitalWrite(spiDataPin, LOW);
  delayMicroseconds(300);
  digitalWrite(spiClockPin, HIGH);
  delayMicroseconds(300);
  
  digitalWrite(spiClockPin, LOW);
  delayMicroseconds(300);
}

void SERIAL_ENABLE_LOW()
{
  delayMicroseconds(100);
 digitalWrite(slaveSelectPin,LOW); 
  delayMicroseconds(100);
}

void SERIAL_ENABLE_HIGH()
{
  delayMicroseconds(100); 
 digitalWrite(slaveSelectPin,HIGH); 
  delayMicroseconds(100);
}

void setup() {
  Serial.begin(9600); // for the serial monitor
  pinMode(buttonPin, INPUT);  // button
  pinMode (slaveSelectPin, OUTPUT); //rx5808
  pinMode (spiDataPin, OUTPUT); //rx5808
  pinMode (spiClockPin, OUTPUT); //rx5808
  digitalWrite(slaveSelectPin, HIGH); //rx5808
  digitalWrite(buttonPin, HIGH); //button
  while (!Serial) {};  // Wait for the Serial port to initialise properly
  Serial.println("Ready");

  Wire.begin(slaveAddress);  // I2C slave address 8 setup.
  Wire.onReceive(i2cReceive);  // register our handler function with the Wire library
  Wire.onRequest(i2cTransmit);  // register data return handler

  commsTable.rssiTrig = lapTrigger; // simulate rssiTrig
  commsTable.channel = 0;  // simulate channel
  printCommsTable();
  setChannelModule(count); //set to channel defined by count
}

void setChannelModule(uint8_t channel)
{
  uint8_t i;
  uint16_t channelData;
  
  //channelData = pgm_read_word(&channelTable[channel]);
  channelData = channelTable[channel];
  
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
  for (i=16;i>0;i--)
  {
    // Is bit high or low?
    if (channelData & 0x1)
    {
      SERIAL_SENDBIT1();
    }
    else
    {
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


void setThreshold() {
  if(lapTrigger == 0){
    uint16_t median;
    for(uint8_t i=0; i < THRESHOLD_ARRAY_SIZE; i++){
      rssiThresholdArray[i] = RSSIread();
    }
    sortArray(rssiThresholdArray, THRESHOLD_ARRAY_SIZE);
    median = getMedian(rssiThresholdArray, THRESHOLD_ARRAY_SIZE);
    if (median > MAGIC_THRESHOLD_REDUCE_CONSTANT){
      lapTrigger = median - MAGIC_THRESHOLD_REDUCE_CONSTANT;
    }
  }
  else {
    lapTrigger = 0;
  }
}

void sortArray(uint16_t a[], uint16_t size) {
    for(uint16_t i=0; i<(size-1); i++) {
        for(uint16_t j=0; j<(size-(i+1)); j++) {
                if(a[j] > a[j+1]) {
                    uint16_t t = a[j];
                    a[j] = a[j+1];
                    a[j+1] = t;
                }
        }
    }
}

uint16_t getMedian(uint16_t a[], uint16_t size) {
    return a[size/2];
}

// Read the RSSI value for the current channel
int RSSIread(){
  int rssi = 0;
  int rssiA = 0;
  for (uint8_t i=0; i<50; i++){
    rssiA += analogRead(0); //Pin A0
  }
  rssiA = rssiA/50; //average of 50 RSSI readings
  rssiA = map(rssiA, 1, 350, 1, 255); //Keep RSSI range from 1 to 255
  rssiA = constrain(rssiA,1, 255); //clip values to only be within this range

  rssiArr[0]=rssiA;
  for(uint8_t i=1; i<=5; i++) {
    rssiArr[i] = (rssiArr[i-1] + rssiArr[i]) >> 1;
  }

  rssi = rssiArr[5];

//  Serial.print("Channel: ");
//  Serial.print(count);
//  Serial.print("  RSSI: ");
//  Serial.println(rssi);

  return rssi;
}

void displayResult()
{
  float h, m, s, ms;
  unsigned long over;
//  String timeString;
  
  elapsed = finished - start;

  h = int(elapsed / 3600000);
  over = elapsed % 3600000;
  m = int(over / 60000);
  over = over % 60000;
  s = int(over / 1000);
  ms = int((over % 1000)/10);

  commsTable.lap = commsTable.lap + 1;

  Serial.print("Lap: ");
  Serial.print(commsTable.lap);
  Serial.print(" Time: ");
//  Serial.print(h, 0);
//  Serial.print("h ");
  Serial.print(m, 0);
  Serial.print("m ");
  Serial.print(s, 0);
  Serial.print("s ");
  Serial.print(ms, 0);
  Serial.println("ms");
  Serial.println();

  commsTable.minutes = m;
  commsTable.seconds = s;
  commsTable.milliseconds = int(ms);
  
//  timeString = String (m,0) +":"+ String(s,0) +":"+ String(ms,0);
//  Serial.println(timeString);
}

void loop() 
{
  rssi = RSSIread();
  if (lapTrigger != 0){
    if(rssi>lapTrigger) {
        if(flag==0)
        { 
          start=millis();
          flag=1;
  
          Serial.println("START");
          commsTable.minutes = 0;
          commsTable.seconds = 0;
          commsTable.milliseconds = 0;
         }
         else {
          finished=millis();
          lapcheck = finished-start;
          if(lapcheck>=minLap){
            displayResult();
            start=millis();
            Serial.println(rssi);
          }
         }
    }
  }
  
  buttonState = digitalRead(buttonPin);
  if (buttonState == LOW) 
  {      
      setThreshold();
      Serial.print("Lap trigger set at: ");
      Serial.println(lapTrigger);
//    count++; 
//    Serial.print("Channel:");
//    Serial.println(count);
//    Serial.println(channelTable[count]);
//    setChannelModule(count);
//              
//    if (count >= 40) 
//    {
//      count = 0;
//    }

  }
  downcount=0;  
  while(digitalRead(buttonPin)== LOW)
  {
    downcount++;
    delay(100);

  }

  if (dataReady) {
    printCommsTable();
    dataReady = false;
  }

  if (commsTable.control > 0) {
//    printTxTable();
    commsTable.control = 0;
  }
        
}

void i2cReceive(int byteCount) {
  // if byteCount is zero, the master only checked for presence
  // of the slave device, triggering this interrupt. No response necessary
  if (byteCount == 0) return;

  // our Interface Specification says commands in range 0x000-0x7F are
  // writes TO this slave, and expects nothing in return.
  // commands in range 0x80-0xFF are reads, requesting data FROM this device
  byte command = Wire.read();
  commsTable.command = command;
  if (command < 0x80) {
    i2cHandleRx(command);
  } else {
    i2cHandleTx(command);
  }
  dataReady = true;
}

/*
   i2cTransmit:
   Parameters: none
   Returns: none
   Next function is called by twi interrupt service when twi detects
   that the Master wants to get data back from the Slave.
   Refer to Interface Specification for details of what data must be sent.
   A transmit buffer (txTable) is populated with the data before sending.
*/
void i2cTransmit() {
  // byte *txIndex = (byte*)&txTable[0];
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
    case 0x00: // send slaveAddress.
      txTable[0] = slaveAddress;
      numBytes = 1;
      break;
    case 0x81:  // send rssiTrig
//      t = int(round(commsTable.temperature * 100));
//      txTable[1] = (byte)(t >> 8);
//      txTable[0] = (byte)(t & 0xFF);
//      numBytes = 2;
      setThreshold();
      commsTable.rssiTrig = lapTrigger;
      txTable[0] = commsTable.rssiTrig;
      numBytes = 1;
      break;
    case 0x82:  // increase lap trigger by 5
      lapTrigger = lapTrigger + 5;
      commsTable.rssiTrig = lapTrigger;
      txTable[0] = commsTable.rssiTrig;
      numBytes = 1;
      break;
    case 0x83:  // decrease lap trigger by 5
      lapTrigger = lapTrigger - 5;
      commsTable.rssiTrig = lapTrigger;
      txTable[0] = commsTable.rssiTrig;
      numBytes = 1;
      break;
    case 0x90: // send minutes, seconds, and milliseconds as an array
      txTable[0] = commsTable.lap;
      txTable[1] = commsTable.minutes;
      txTable[2] = commsTable.seconds;
      txTable[3] = commsTable.milliseconds;
      numBytes = 4;
      break;
    case 0x91: // send minutes channel
      txTable[0] = commsTable.minutes;
      numBytes = 1;
      break;
    case 0x92: // send seconds channel
      txTable[0] = commsTable.seconds;
      numBytes = 1;
      break;
    case 0x93: // send milliseconds channel
      txTable[0] = commsTable.milliseconds;
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

/*
   i2cHandleRx:
   Parameters: byte, the first byte sent by the I2C master.
   returns: byte, number of bytes read, or 0xFF if error
   If the MSB of 'command' is 0, then master is sending only.
   Handle the data reception in this function.
*/
byte i2cHandleRx(byte command) {
  // If you are here, the I2C Master has sent data
  // using one of the SMBus write commands.
  byte result = 0;
  // returns the number of bytes read, or FF if unrecognised
  // command or mismatch between data expected and received

  switch (command) {
    case 0x0A:  // read three bytes in a block to set brightness and color
      if (Wire.available() == 3) { // good write from Master
        commsTable.minutes = Wire.read();
        commsTable.seconds = Wire.read();
        commsTable.milliseconds = Wire.read();
        result = 3;
      } else {
        result = 0xFF;
      }
      break;

    case 0x0B: // read the byte and reset the lap counter and flag
      if (Wire.available() == 1) { // good write from Master
        commsTable.lap = Wire.read();
        flag =0;
        result = 1;
      } else {
        result = 0xFF;
      }
      break;

    case 0x0C: // read the byte and reset the lap trigger to the assigned value
      if (Wire.available() == 1) { // good write from Master
        lapTrigger = Wire.read();
        Serial.print("Command from RPi - Lap trigger set at: ");
        Serial.println(lapTrigger);
        result = 1;
      } else {
        result = 0xFF;
      }
      break;

    case 0x0D:
      if (Wire.available() == 1) { // good write from Master
        commsTable.milliseconds = Wire.read();
        result = 1;
      } else {
        result = 0xFF;
      }
      break;

    default:
      result = 0xFF;
  }

  if (result == 0xFF) commsTable.control |= rxFault;
  return result;

}

/*
   i2cHandleTx:
   Parameters: byte, the first byte sent by master
   Returns: number of bytes received, or 0xFF if error
   Used to handle SMBus process calls
*/
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

void printCommsTable() {
  String builder = "";
  builder = "commsTable contents:";
  Serial.println(builder);
  builder = "  command: ";
  builder += String(commsTable.command, HEX);
  Serial.println(builder);
  builder = "  control: ";
  builder += String(commsTable.control, HEX);
  Serial.println(builder);
  builder = "  RSSI Triger: ";
  builder += commsTable.rssiTrig;
//  builder += (char)186;  // the "º" symbol
  builder += " dB";
  Serial.println(builder);
  builder = "  Channel: ";
  builder += commsTable.channel;
//  builder += " lux";
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

