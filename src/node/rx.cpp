#include "config.h"
#include "rx.h"
#include "hardware.h"
#include "microclock.h"

constexpr uint8_t SYNTHESIZER_REGISTER_A = 0x00;
constexpr uint8_t SYNTHESIZER_REGISTER_B = 0x01;
constexpr uint8_t SYNTHESIZER_REGISTER_C = 0x02;
constexpr uint8_t SYNTHESIZER_REGISTER_D = 0x03;
constexpr uint8_t VCO_SWITCHCAP_CONTROL_REGISTER = 0x04;
constexpr uint8_t DFC_CONTROL_REGISTER = 0x05;
constexpr uint8_t _6M_AUDIO_DEMODULATOR_CONTROL_REGISTER = 0x06;
constexpr uint8_t _6M5_AUDIO_DEMODULATOR_CONTROL_REGISTER = 0x07;
constexpr uint8_t RECEIVER_CONTROL_REGISTER_1 = 0x08;
constexpr uint8_t RECEIVER_CONTROL_REGISTER_2 = 0x09;
constexpr uint8_t POWER_DOWN_CONTROL_REGISTER = 0x0A;
constexpr uint8_t STATE_REGISTER = 0x0F;

constexpr mtime_t RX5808_MIN_BUSTIME = 30;  // after set freq need to wait this long before setting again

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

const bool RxModule::checkBusAvailable()
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

    spiWrite(STATE_REGISTER, 0x00);

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
    spiWrite(SYNTHESIZER_REGISTER_B, vtxHex);

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

    spiWrite(POWER_DOWN_CONTROL_REGISTER, options);

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
    pinMode(clkPin, OUTPUT);
    pinMode(dataPin, OUTPUT);
    digitalWrite(clkPin, LOW);
    digitalWrite(dataPin, LOW);
}

void BitBangRxModule::spiWrite(uint8_t addr, uint32_t data)
{
    digitalWrite(selPin, LOW); // Enable chip select
    bitBang(addr, 4);
    serialSendBit(true);  // Write to register
    bitBang(data, 20);
    digitalWrite(selPin, HIGH);  // Finished clocking data in
    digitalWrite(dataPin, LOW);
}

template <typename T> const void BitBangRxModule::bitBang(T bits, const uint_fast8_t size)
{
    for (uint_fast8_t i = size; i > 0; i--)
    {
        serialSendBit(bits & 0x1); // Is bit high or low?
        bits >>= 1;  // Shift bits along to check the next one
    }
}

// numbers chosen to give approx 4us clock period (2us high + 2us low)
#define DATA_CLOCK_DELAY 1
#define CLOCK_HIGH_PERIOD 2
#define CLOCK_DATA_DELAY 1

inline const void BitBangRxModule::serialSendBit(const bool b)
{
    digitalWrite(dataPin, b ? HIGH : LOW);
    delayMicroseconds(DATA_CLOCK_DELAY);
    digitalWrite(clkPin, HIGH);
    delayMicroseconds(CLOCK_HIGH_PERIOD);
    digitalWrite(clkPin, LOW);
    delayMicroseconds(CLOCK_DATA_DELAY);
}


#if TARGET == ESP32_TARGET
#include <SPI.h>

void NativeRxModule::spiInit()
{
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
