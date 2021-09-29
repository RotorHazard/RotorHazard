#include "config.h"
#include "commands.h"
#include "hardware.h"

#ifdef USE_I2C
#include <Wire.h>

static void i2cOnReceive(int byteCount);
static void i2cOnRequest();

static volatile bool i2cReadyForReceive;
static volatile uint8_t i2cCommand = INVALID_COMMAND;
static volatile uint8_t i2cPayload[BUFFER_LENGTH-1]; // BUFFER_LENGTH declared in Wire.h
static volatile uint8_t i2cPayloadSize;

void i2cInit(uint8_t i2cAddress, bool reset) {
    hardware.setStatusLed(true);
    if (reset) {
        Wire.end();  // release I2C pins (SDA & SCL), in case they are "stuck"
        delay(250);  //  to help bus reset and show longer LED flash
    }
    hardware.setStatusLed(false);

    Wire.begin(i2cAddress);
    Wire.onReceive(i2cOnReceive);
    Wire.onRequest(i2cOnRequest);

    TWAR = (i2cAddress << 1) | 1;  // enable broadcasts to be received
}

void i2cEventRun() {
    if (!i2cReadyForReceive) {
        Message msg;
        msg.command = i2cCommand;
        for (int_fast8_t i = 0; i < i2cPayloadSize; i++) {
            msg.buffer.data[i] = i2cPayload[i];
        }
        msg.buffer.index = i2cPayloadSize;
        msg.buffer.size = i2cPayloadSize;
        i2cCommand = INVALID_COMMAND;
        i2cPayloadSize = 0;
        i2cReadyForReceive = true;
        validateAndProcessWriteCommand(msg, I2C_SOURCE);
    }
}

void i2cOnReceive(int bytesAvailable) {
    if (i2cReadyForReceive && bytesAvailable > 0) {
        i2cCommand = Wire.read();
        i2cPayloadSize = bytesAvailable - 1;
        for (int_fast8_t i = 0; i<i2cPayloadSize; i++) {
            i2cPayload[i] = Wire.read();
        }
        if (isWriteCommand(i2cCommand)) {
            i2cReadyForReceive = false;
        }
    }
}

void i2cOnRequest() {
    Message msg;
    msg.command = i2cCommand;
    msg.handleReadCommand(I2C_SOURCE);
    sendReadCommandResponse(Wire, msg);
    i2cCommand = INVALID_COMMAND;
}

#endif
