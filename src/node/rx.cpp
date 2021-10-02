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

// Calculate rx5808 register hex value for given frequency in MHz
static uint16_t freqMhzToRegVal(freq_t freqInMhz)
{
    uint16_t tf, N, A;
    tf = (freqInMhz - 479) / 2;
    N = tf / 32;
    A = tf % 32;
    return (N << 7) + A;
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
void RxModule::reset()
{  
    spiWrite(STATE_REGISTER, 0x00);
    powerUp();
}

// Set the frequency given on the rx5808 module
void RxModule::setFrequency(freq_t frequency)
{
    // Get the hex value to send to the rx module
    uint16_t vtxHex = freqMhzToRegVal(frequency);

    //Channel data from the lookup table, 20 bytes of register data are sent, but the MSB 4 bits are zeros.
    // register address = 0x1, write, data0-15=vtxHex data15-19=0x0
    spiWrite(SYNTHESIZER_REGISTER_B, vtxHex);
}

// Set power options on the rx5808 module
void RxModule::setPower(uint32_t options)
{
    spiWrite(POWER_DOWN_CONTROL_REGISTER, options);
}

// Set up rx5808 module (disabling unused features to save some power)
void RxModule::powerUp()
{
    setPower(0b11010000110111110011);
    rxPoweredDown = false;
}

// Power down rx5808 module
void RxModule::powerDown()
{   
    setPower(0b11111111111111111111);
    rxPoweredDown = true;
}

// Read the RSSI value for the current channel
rssi_t RxModule::readRssi()
{
    return hardware.readADC(rssiPin);
}



/*
 * Bit-bang SPI implementation.
 */

#define SPI_CHILL_TIME 5
// SPI clock speed should be about 100KHz (10us clock period)
#define SPI_DATA_CLOCK_DELAY 2
#define SPI_CLOCK_HIGH_PERIOD 5
#define SPI_CLOCK_DATA_DELAY 2

void BitBangRxModule::spiInit()
{
    pinMode(clkPin, OUTPUT);
    pinMode(dataPin, OUTPUT);
    digitalWrite(clkPin, LOW);
    digitalWrite(dataPin, LOW);
}

void BitBangRxModule::spiWrite(uint8_t addr, uint32_t data)
{
    delayMicroseconds(SPI_CHILL_TIME); // Delay between writes
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

inline const void BitBangRxModule::serialSendBit(const bool b)
{
    digitalWrite(dataPin, b ? HIGH : LOW);
    delayMicroseconds(SPI_DATA_CLOCK_DELAY);
    digitalWrite(clkPin, HIGH);
    delayMicroseconds(SPI_CLOCK_HIGH_PERIOD);
    digitalWrite(clkPin, LOW);
    delayMicroseconds(SPI_CLOCK_DATA_DELAY);
}



/*
 * Native SPI implementation.
 */

#if TARGET == ESP32_TARGET
#include <SPI.h>

void NativeRxModule::spiInit()
{
    SPI.begin(clkPin, -1, dataPin);
}

void NativeRxModule::spiWrite(uint8_t addr, uint32_t data)
{
    uint32_t payload = addr | (1 << 4) | (data << 5);
    // SPI clock speed should be 100KHz
    SPI.beginTransaction(SPISettings(100000, LSBFIRST, SPI_MODE0));
    digitalWrite(selPin, LOW);
    SPI.transferBits(payload, NULL, 25);
    digitalWrite(selPin, HIGH);
    SPI.endTransaction();
}
#endif
