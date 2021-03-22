#include "config.h"
#include "rx.h"
#include "hardware.h"
#include "microclock.h"

constexpr mtime_t RX5808_MIN_BUSTIME = 30;  // after set freq need to wait this long before setting again

// Functions for the rx5808 module

mtime_t RxModule::lastBusTimeMs = 0;

// Calculate rx5808 register hex value for given frequency in MHz
static uint16_t freqMhzToRegVal(freq_t freqInMhz)
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

void RxModule::init(uint8_t dataPin, uint8_t clkPin, uint8_t selPin, uint8_t rssiPin)
{
    this->dataPin = dataPin;
    this->clkPin = clkPin;
    this->selPin = selPin;
    this->rssiPin = rssiPin;

    spiInit();
}

// Reset rx5808 module to wake up from power down
bool RxModule::reset()
{  
    bool avail = checkBusAvailable();
    if (!avail) {
        return false;
    }

    spiWrite(0xF, 0x00);

    return powerUp();
}

// Set the frequency given on the rx5808 module
bool RxModule::setFrequency(freq_t frequency)
{
    bool avail = checkBusAvailable();
    if (!avail) {
        return false;
    }

    // Get the hex value to send to the rx module
    uint16_t vtxHex = freqMhzToRegVal(frequency);

    //Channel data from the lookup table, 20 bytes of register data are sent, but the MSB 4 bits are zeros.
    // register address = 0x1, write, data0-15=vtxHex data15-19=0x0
    spiWrite(0x1, vtxHex);
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

    spiWrite(0xA, options);

    digitalWrite(dataPin, LOW);

    lastBusTimeMs = usclock.millis();
    return true;
}

// Set up rx5808 module (disabling unused features to save some power)
bool RxModule::powerUp()
{
    bool rc = setPower(0b11010000110111110011);
    if (rc) {
        rxPoweredDown = false;
    }
    return rc;
}

// Power down rx5808 module
bool RxModule::powerDown()
{   
    bool rc = setPower(0b11111111111111111111);
    if (rc) {
        rxPoweredDown = true;
    }
    return rc;
}

// Read the RSSI value for the current channel
rssi_t RxModule::readRssi()
{
    return hardware.readADC(rssiPin);
}


void BitBangRxModule::spiInit()
{
    pinMode(dataPin, OUTPUT);
    pinMode(selPin, OUTPUT);
    pinMode(clkPin, OUTPUT);
    digitalWrite(selPin, HIGH);
    digitalWrite(clkPin, LOW);
    digitalWrite(dataPin, LOW);
}

void BitBangRxModule::spiWrite(uint8_t addr, uint32_t data)
{
    serialEnableHigh();
    serialEnableLow();
    bitBang(addr, 4);
    serialSendBit1();  // Write to register
    bitBang(data, 20);
    serialEnableHigh();  // Finished clocking data in
}

template <typename T> void BitBangRxModule::bitBang(T bits, const uint_fast8_t size)
{
    for (uint_fast8_t i = size; i > 0; i--)
    {
        if (bits & 0x1)
        {  // Is bit high or low?
            serialSendBit1();
        }
        else
        {
            serialSendBit0();
        }
        bits >>= 1;  // Shift bits along to check the next one
    }
}

void BitBangRxModule::serialSendBit0()
{
    digitalWrite(dataPin, LOW);
    delayMicroseconds(300);
    digitalWrite(clkPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(clkPin, LOW);
    delayMicroseconds(300);
}

void BitBangRxModule::serialSendBit1()
{
    digitalWrite(dataPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(clkPin, HIGH);
    delayMicroseconds(300);
    digitalWrite(clkPin, LOW);
    delayMicroseconds(300);
}

void BitBangRxModule::serialEnableLow()
{
    digitalWrite(selPin, LOW);
    delayMicroseconds(200);
}

void BitBangRxModule::serialEnableHigh()
{
    digitalWrite(selPin, HIGH);
    delayMicroseconds(200);
}

#if TARGET == ESP32_TARGET
#include <SPI.h>

void NativeRxModule::spiInit()
{
    pinMode(selPin, OUTPUT);
    digitalWrite(selPin, HIGH);
    SPI.begin(clkPin, -1, dataPin);
}

void NativeRxModule::spiWrite(uint8_t addr, uint32_t data)
{
    uint32_t payload = addr | (1 << 4) | (data << 5);
    SPI.beginTransaction(SPISettings(1000000, LSBFIRST, SPI_MODE0));
    digitalWrite(selPin, LOW);
    SPI.transferBits(payload, NULL, 25);
    digitalWrite(selPin, HIGH);
    SPI.endTransaction();
}
#endif
