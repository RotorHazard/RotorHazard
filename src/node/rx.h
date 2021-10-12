#ifndef rx_h
#define rx_h

#include "util/rhtypes.h"

/**
 * Functions for the rx5808 module.
 * See RTC6715 datasheet for spec.
 */
class RxModule {
private:
    bool rxPoweredDown = false;

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
    void setFrequency(freq_t frequency);
    void setPower(uint32_t options);
    rssi_t readRssi();
    void powerUp();
    void powerDown();
    const bool isPoweredDown() { return rxPoweredDown; }
    void reset();
};

class BitBangRxModule final : public RxModule {
private:
    template <typename T> const void bitBang(T bits, uint_fast8_t size);
    inline const void serialSendBit(bool b);

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
