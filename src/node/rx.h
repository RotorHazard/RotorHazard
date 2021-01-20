#ifndef rx_h
#define rx_h

#include "util/rhtypes.h"

class RxModule {
  private:
    bool rxPoweredDown = false;
  public:
    void setup();
    void setFrequency(uint16_t frequency);
    void setPower(uint32_t options);
    rssi_t readRssi();
    void powerDown();
    bool isPoweredDown() { return rxPoweredDown; };
    void reset();
};

#endif
