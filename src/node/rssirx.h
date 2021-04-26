#ifndef rssirx_h
#define rssirx_h

#include "config.h"
#include "rssi.h"
#include "rx.h"

class RssiReceivers {
public:
    RssiReceivers() = default;
    RssiReceivers(const RssiReceivers&) = delete;
    RssiReceivers(RssiReceivers&&) = delete;
    RssiReceivers& operator=(const RssiReceivers&) = delete;
    RssiReceivers& operator=(RssiReceivers&&) = delete;

    virtual RssiNode& getRssiNode(uint_fast8_t idx) = 0;
    virtual RxModule& getRxModule(uint_fast8_t idx) = 0;
    virtual Settings& getSettings(uint_fast8_t idx) = 0;
    uint_fast8_t getSlotIndex(uint_fast8_t idx) const { return idx; }
    virtual uint_fast8_t getCount() const = 0;
    virtual void start(mtime_t ms, utime_t us) = 0;
    virtual bool readRssi(mtime_t ms, utime_t us) = 0;
};

extern RssiReceivers& rssiRxs;

#endif
