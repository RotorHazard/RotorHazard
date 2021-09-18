#include "config.h"
#include "hardware.h"
#include "commands.h"

#define SERIAL_BAUD_RATE 500000

#define SERIALCOM Serial

class Esp32Hardware : public Hardware {
private:
    uint8_t rx5808SelPinForNodeIndex(uint_fast8_t nIdx)
    {
        switch (nIdx)
        {
            case 0:
                return RX5808_SEL0_PIN;
            case 1:
                return RX5808_SEL1_PIN;
            case 2:
                return RX5808_SEL2_PIN;
            case 3:
                return RX5808_SEL3_PIN;
            case 4:
                return RX5808_SEL4_PIN;
            case 5:
                return RX5808_SEL5_PIN;
            default:
                return RX5808_SEL0_PIN;
        }
    }

    uint8_t rssiInputPinForNodeIndex(uint_fast8_t nIdx)
    {
        switch (nIdx)
        {
            case 0:
                return RSSI_INPUT0_PIN;
            case 1:
                return RSSI_INPUT1_PIN;
            case 2:
                return RSSI_INPUT2_PIN;
            case 3:
                return RSSI_INPUT3_PIN;
            case 4:
                return RSSI_INPUT4_PIN;
            case 5:
                return RSSI_INPUT5_PIN;
            default:
                return RSSI_INPUT0_PIN;
        }
    }

public:
    Esp32Hardware() : Hardware(HIGH,LOW) {
    }
    void init()
    {
        Hardware::init();

        // turn-off all SPI chip selects
        for (uint_fast8_t i=0; i<RX5808_SEL_PIN_COUNT; i++) {
            uint8_t selPin = rx5808SelPinForNodeIndex(i);
            pinMode(selPin, OUTPUT);
            digitalWrite(selPin, HIGH);
        }

        analogReadResolution(10);
        analogSetAttenuation(ADC_6db);

        SERIALCOM.begin(SERIAL_BAUD_RATE);  // Start serial interface
        while (!SERIALCOM) {
            delay(1);  // Wait for the Serial port to initialize
        }
    }

    void initRxModule(uint_fast8_t nIdx, RxModule& rx)
    {
        uint8_t dataPin = MOSI;  //DATA (CH1) output line to (all) RX5808 modules
        uint8_t clkPin = SCK;   //CLK (CH3) output line to (all) RX5808 modules
        uint8_t selPin = rx5808SelPinForNodeIndex(nIdx);  //SEL (CH2) output line to RX5808 module
        uint8_t rssiPin = rssiInputPinForNodeIndex(nIdx); //RSSI input from RX5808
        rx.init(dataPin, clkPin, selPin, rssiPin);
    }

    const char* getProcessorType() {
      return "ESP32";
    }

    uint8_t readADC(uint8_t pin) {
        int raw = analogRead(pin);
        // rescale to fit into a byte
        return raw >> 2;
    }
};
