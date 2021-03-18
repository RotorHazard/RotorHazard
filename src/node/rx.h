#ifndef rx_h
#define rx_h

#include "util/rhtypes.h"

// currently just RX5808 but could be abstract with sub-classes
class RxModule {
  private:
    uint8_t dataPin = 0;
    uint8_t clkPin = 0;
    uint8_t selPin = 0;
    uint8_t rssiPin = 0;
    bool rxPoweredDown = false;
    static mtime_t lastBusTimeMs;

    void serialSendBit0();
    void serialSendBit1();
    void serialEnableLow();
    void serialEnableHigh();
    static bool checkBusAvailable();
  public:
    RxModule() = default;
    RxModule(const RxModule&) = delete;
    RxModule(RxModule&&) = delete;
    RxModule& operator=(const RxModule&) = delete;
    RxModule& operator=(RxModule&&) = delete;

    void init(uint8_t dataPin, uint8_t clkPin, uint8_t selPin, uint8_t rssiPin);
    bool setFrequency(freq_t frequency);
    bool setPower(uint32_t options);
    rssi_t readRssi();
    bool powerUp();
    bool powerDown();
    bool isPoweredDown() { return rxPoweredDown; }
    bool reset();
};

#endif
