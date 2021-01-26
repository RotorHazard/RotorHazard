#ifndef rx_h
#define rx_h

#include "util/rhtypes.h"

// currently just RX5808 but could be abstract with sub-classes
class RxModule {
  private:
    uint16_t dataPin = 0;
    uint16_t clkPin = 0;
    uint16_t selPin = 0;
    uint16_t rssiInputPin = 0;
    bool rxPoweredDown = false;
    static mtime_t lastBusTimeMs;

    void serialSendBit0();
    void serialSendBit1();
    void serialEnableLow();
    void serialEnableHigh();
    static bool checkBusAvailable();
  public:
    void init(uint16_t dataPin, uint16_t clkPin, uint16_t selPin, uint16_t rssiPin);
    bool setFrequency(uint16_t frequency);
    bool setPower(uint32_t options);
    rssi_t readRssi();
    bool powerUp();
    bool powerDown();
    bool isPoweredDown() { return rxPoweredDown; }
    bool reset();
};

#endif
