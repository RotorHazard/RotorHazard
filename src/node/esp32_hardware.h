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
                return 16;
            case 1:
                return 5;
            case 2:
                return 4;
            case 3:
                return 15;
            case 4:
                return 25;
            default:
                return 26;
        }
    }

    uint8_t rssiInputPinForNodeIndex(uint_fast8_t nIdx)
    {
        switch (nIdx)
        {
            case 0:
                return A0;
            case 1:
                return A3;
            case 2:
                return A6;
            case 3:
                return A7;
            case 4:
                return A4;
            default:
                return A5;
        }
    }

public:
    Esp32Hardware() : Hardware(HIGH,LOW) {
    }
    void init()
    {
        Hardware::init();

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
