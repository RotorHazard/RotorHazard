#ifndef rssirx_h
#define rssirx_h

#include "config.h"
#include "rssi.h"
#include "rx.h"

class RssiReceivers {
public:
    static RssiReceivers *rssiRxs;

    virtual RssiNode& getRssiNode(uint8_t idx) = 0;
    virtual RxModule& getRxModule(uint8_t idx) = 0;
    virtual Settings& getSettings(uint8_t idx) = 0;
    virtual uint8_t getCount() = 0;
    virtual void start() = 0;
    virtual bool readRssi() = 0;
};
#endif
