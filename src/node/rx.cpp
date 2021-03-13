#include "config.h"
#include "rx.h"
#include "microclock.h"

constexpr mtime_t RX5808_MIN_BUSTIME = 30;  // after set freq need to wait this long before setting again

// Functions for the rx5808 module

mtime_t RxModule::lastBusTimeMs = 0;

// Calculate rx5808 register hex value for given frequency in MHz
static uint16_t freqMhzToRegVal(uint16_t freqInMhz)
{
    uint16_t tf, N, A;
    tf = (freqInMhz - 479) / 2;
    N = tf / 32;
    A = tf % 32;
    return (N << 7) + A;
}

bool RxModule::checkBusAvailable()
{
    mtime_t timeVal = usclock.millis() - lastBusTimeMs;
    return timeVal >= RX5808_MIN_BUSTIME;
}

void RxModule::init(uint16_t dataPin, uint16_t clkPin, uint16_t selPin, uint16_t rssiPin)
{
    this->dataPin = dataPin;
    this->clkPin = clkPin;
    this->selPin = selPin;
    this->rssiInputPin = rssiPin;

    pinMode(dataPin, OUTPUT);
    pinMode(selPin, OUTPUT);
    pinMode(clkPin, OUTPUT);
    digitalWrite(selPin, HIGH);
    digitalWrite(clkPin, LOW);
    digitalWrite(dataPin, LOW);
}

// Reset rx5808 module to wake up from power down
bool RxModule::reset()
{  
    bool avail = checkBusAvailable();
    if (!avail) {
        return false;
    }

    serialEnableHigh();
    serialEnableLow();

    serialSendBit1();  // Register 0xF
    serialSendBit1();
    serialSendBit1();
    serialSendBit1();

    serialSendBit1();  // Write to register

    for (uint8_t i = 20; i > 0; i--) {
        serialSendBit0();
    }

    serialEnableHigh();  // Finished clocking data in

    return powerUp();
}

// Set the frequency given on the rx5808 module
bool RxModule::setFrequency(uint16_t frequency)
{
    bool avail = checkBusAvailable();
    if (!avail) {
        return false;
    }

    // Get the hex value to send to the rx module
    uint16_t vtxHex = freqMhzToRegVal(frequency);

    //Channel data from the lookup table, 20 bytes of register data are sent, but the
    // MSB 4 bits are zeros register address = 0x1, write, data0-15=vtxHex data15-19=0x0
    serialEnableHigh();
    serialEnableLow();

    serialSendBit1();  // Register 0x1
    serialSendBit0();
    serialSendBit0();
    serialSendBit0();

    serialSendBit1();  // Write to register

    // D0-D15, note: loop runs backwards as more efficent on AVR
    for (uint8_t i = 16; i > 0; i--)
    {
        if (vtxHex & 0x1)
        {  // Is bit high or low?
            serialSendBit1();
        }
        else
        {
            serialSendBit0();
        }
        vtxHex >>= 1;  // Shift bits along to check the next one
    }

    for (uint8_t i = 4; i > 0; i--) { // Remaining D16-D19
        serialSendBit0();
    }

    serialEnableHigh();  // Finished clocking data in
    delay(2);

    digitalWrite(clkPin, LOW);
    digitalWrite(dataPin, LOW);

    lastBusTimeMs = usclock.millis();  // mark time of last tune of RX5808 to freq
    return true;
}

// Set power options on the rx5808 module
bool RxModule::setPower(uint32_t options)
{
    bool avail = checkBusAvailable();
    if (!avail) {
        return false;
    }

    serialEnableHigh();
    serialEnableLow();

    serialSendBit0();  // Register 0xA
    serialSendBit1();
    serialSendBit0();
    serialSendBit1();

    serialSendBit1();  // Write to register

    for (uint8_t i = 20; i > 0; i--)
    {
        if (options & 0x1)
        {  // Is bit high or low?
            serialSendBit1();
        }
        else
        {
            serialSendBit0();
        }
        options >>= 1;  // Shift bits along to check the next one
    }

    serialEnableHigh();  // Finished clocking data in

    digitalWrite(dataPin, LOW);

    lastBusTimeMs = usclock.millis();
    return true;
}

// Set up rx5808 module (disabling unused features to save some power)
bool RxModule::powerUp()
{
    bool rc = setPower(0b11010000110111110011);
    if (rc)
        rxPoweredDown = false;
    return rc;
}

// Power down rx5808 module
bool RxModule::powerDown()
{   
    bool rc = setPower(0b11111111111111111111);
    if (rc)
        rxPoweredDown = true;
    return rc;
}

// Read the RSSI value for the current channel
rssi_t RxModule::readRssi()
{
    // reads 5V value as 0-1023, RX5808 is 3.3V powered so RSSI pin will never output the full range
    int raw = analogRead(rssiInputPin);
    // clamp upper range to fit scaling
    if (raw > 0x01FF)
        raw = 0x01FF;
    // rescale to fit into a byte and remove some jitter
    return raw >> 1;
}

void RxModule::serialSendBit0()
{
    digitalWrite(dataPin, LOW);
    delayMicroseconds(300);
    digitalWrite(clkPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(clkPin, LOW);
    delayMicroseconds(300);
}

void RxModule::serialSendBit1()
{
    digitalWrite(dataPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(clkPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(clkPin, LOW);
    delayMicroseconds(300);
}

void RxModule::serialEnableLow()
{
    digitalWrite(selPin, LOW);
    delayMicroseconds(200);
}

void RxModule::serialEnableHigh()
{
    digitalWrite(selPin, HIGH);
    delayMicroseconds(200);
}
