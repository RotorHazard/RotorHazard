#ifndef rx_h
#define rx_h

#include "util/rhtypes.h"

// currently just RX5808 but could be abstract with sub-classes
class RxModule {
private:
    bool rxPoweredDown = false;
    static mtime_t lastBusTimeMs;
    static bool checkBusAvailable();

protected:
    uint8_t dataPin = 0;
    uint8_t clkPin = 0;
    uint8_t selPin = 0;
    uint8_t rssiPin = 0;
    virtual void spiInit() = 0;
    virtual void spiWrite(uint8_t addr, uint32_t data) = 0;

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

class BitBangRxModule final : public RxModule {
private:
    template <typename T> void bitBang(T bits, const uint_fast8_t size);
    void serialSendBit0();
    void serialSendBit1();
    void serialEnableLow();
    void serialEnableHigh();

protected:
    void spiInit();
    void spiWrite(uint8_t addr, uint32_t data);
};

#if TARGET == ESP32_TARGET
class NativeRxModule final : public RxModule {
protected:
    void spiInit();
    void spiWrite(uint8_t addr, uint32_t data);
};
#endif
#endif
