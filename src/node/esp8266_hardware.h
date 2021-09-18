#include "config.h"
#include "hardware.h"
#include "commands.h"

#define SERIAL_BAUD_RATE 500000

#define SERIALCOM Serial

class Esp8266Hardware : public Hardware {
public:
    Esp8266Hardware() : Hardware(HIGH,LOW) {
    }
    void init()
    {
        Hardware::init();

        // turn-off all SPI chip selects
        pinMode(RX5808_SEL_PIN, OUTPUT);
        digitalWrite(RX5808_SEL_PIN, HIGH);

        SERIALCOM.begin(SERIAL_BAUD_RATE);  // Start serial interface
        while (!SERIALCOM) {
            delay(1);  // Wait for the Serial port to initialize
        }
    }

    void initRxModule(uint_fast8_t nIdx, RxModule& rx)
    {
        uint8_t dataPin = MOSI;  //DATA (CH1) output line to (all) RX5808 modules
        uint8_t clkPin = SCK;   //CLK (CH3) output line to (all) RX5808 modules
        uint8_t selPin = RX5808_SEL_PIN;  //SEL (CH2) output line to RX5808 module
        uint8_t rssiPin = RSSI_INPUT_PIN; //RSSI input from RX5808
        rx.init(dataPin, clkPin, selPin, rssiPin);
    }

    const char* getProcessorType() {
      return "ESP8266";
    }

    uint8_t readADC(uint8_t pin) {
        int raw = analogRead(pin);
        // rescale to fit into a byte
        return raw >> 2;
    }
};
