#include "config.h"
#include "rx.h"

// Functions for the rx5808 module

static void SERIAL_SENDBIT1()
{
    digitalWrite(RX5808_DATA_PIN, HIGH);
    delayMicroseconds(300);
    digitalWrite(RX5808_CLK_PIN, HIGH);
    delayMicroseconds(300);
    digitalWrite(RX5808_CLK_PIN, LOW);
    delayMicroseconds(300);
}

static void SERIAL_SENDBIT0()
{
    digitalWrite(RX5808_DATA_PIN, LOW);
    delayMicroseconds(300);
    digitalWrite(RX5808_CLK_PIN, HIGH);
    delayMicroseconds(300);
    digitalWrite(RX5808_CLK_PIN, LOW);
    delayMicroseconds(300);
}

static void SERIAL_ENABLE_LOW()
{
    digitalWrite(RX5808_SEL_PIN, LOW);
    delayMicroseconds(200);
}

static void SERIAL_ENABLE_HIGH()
{
    digitalWrite(RX5808_SEL_PIN, HIGH);
    delayMicroseconds(200);
}

// Calculate rx5808 register hex value for given frequency in MHz
static uint16_t freqMhzToRegVal(uint16_t freqInMhz)
{
    uint16_t tf, N, A;
    tf = (freqInMhz - 479) / 2;
    N = tf / 32;
    A = tf % 32;
    return (N << 7) + A;
}

// Reset rx5808 module to wake up from power down
void RxModule::reset()
{  
    SERIAL_ENABLE_HIGH();
    SERIAL_ENABLE_LOW();

    SERIAL_SENDBIT1();  // Register 0xF
    SERIAL_SENDBIT1();
    SERIAL_SENDBIT1();
    SERIAL_SENDBIT1();

    SERIAL_SENDBIT1();  // Write to register

    for (uint8_t i = 20; i > 0; i--)
        SERIAL_SENDBIT0();

    SERIAL_ENABLE_HIGH();  // Finished clocking data in

    setup();
}
// Set the frequency given on the rx5808 module
void RxModule::setFrequency(uint16_t frequency)
{
    // Get the hex value to send to the rx module
    uint16_t vtxHex = freqMhzToRegVal(frequency);

    //Channel data from the lookup table, 20 bytes of register data are sent, but the
    // MSB 4 bits are zeros register address = 0x1, write, data0-15=vtxHex data15-19=0x0
    SERIAL_ENABLE_HIGH();
    SERIAL_ENABLE_LOW();

    SERIAL_SENDBIT1();  // Register 0x1
    SERIAL_SENDBIT0();
    SERIAL_SENDBIT0();
    SERIAL_SENDBIT0();

    SERIAL_SENDBIT1();  // Write to register

    // D0-D15, note: loop runs backwards as more efficent on AVR
    for (uint8_t i = 16; i > 0; i--)
    {
        if (vtxHex & 0x1)
        {  // Is bit high or low?
            SERIAL_SENDBIT1();
        }
        else
        {
            SERIAL_SENDBIT0();
        }
        vtxHex >>= 1;  // Shift bits along to check the next one
    }

    for (uint8_t i = 4; i > 0; i--)  // Remaining D16-D19
        SERIAL_SENDBIT0();

    SERIAL_ENABLE_HIGH();  // Finished clocking data in

}

// Set power options on the rx5808 module
void RxModule::setPower(uint32_t options)
{
    SERIAL_ENABLE_HIGH();
    SERIAL_ENABLE_LOW();

    SERIAL_SENDBIT0();  // Register 0xA
    SERIAL_SENDBIT1();
    SERIAL_SENDBIT0();
    SERIAL_SENDBIT1();

    SERIAL_SENDBIT1();  // Write to register

    for (uint8_t i = 20; i > 0; i--)
    {
        if (options & 0x1)
        {  // Is bit high or low?
            SERIAL_SENDBIT1();
        }
        else
        {
            SERIAL_SENDBIT0();
        }
        options >>= 1;  // Shift bits along to check the next one
    }

    SERIAL_ENABLE_HIGH();  // Finished clocking data in

    digitalWrite(RX5808_DATA_PIN, LOW);
}

// Power down rx5808 module
void RxModule::powerDown() 
{   
    setPower(0b11111111111111111111);
    rxPoweredDown = true;
}

// Set up rx5808 module (disabling unused features to save some power)
void RxModule::setup() 
{   
    setPower(0b11010000110111110011);
    rxPoweredDown = false;
}


// Read the RSSI value for the current channel
rssi_t RxModule::readRssi()
{
    // reads 5V value as 0-1023, RX5808 is 3.3V powered so RSSI pin will never output the full range
    int raw = analogRead(RSSI_INPUT_PIN);
    // clamp upper range to fit scaling
    if (raw > 0x01FF)
        raw = 0x01FF;
    // rescale to fit into a byte and remove some jitter
    return raw >> 1;
}
