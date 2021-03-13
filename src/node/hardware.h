#ifndef hardware_h
#define hardware_h

#include "rssi.h"
#include "rx.h"

// features flags for value returned by READ_RHFEAT_FLAGS command
#define RHFEAT_STM32_MODE ((uint16_t)0x0004)      // STM 32-bit processor running multiple nodes
#define RHFEAT_JUMPTO_BOOTLDR ((uint16_t)0x0008)  // JUMP_TO_BOOTLOADER command supported
#define RHFEAT_IAP_FIRMWARE ((uint16_t)0x0010)    // in-application programming of firmware supported
#define RHFEAT_NONE ((uint16_t)0)

// dummy macro
#define LOG_ERROR(...)

class Hardware {
private:
    const uint8_t ledOnValue, ledOffValue;

protected:
    bool currentStatusLedFlag = false;

public:
    Hardware(uint8_t ledOn, uint8_t ledOff) : ledOnValue(ledOn), ledOffValue(ledOff) {
    }
    Hardware(const Hardware&) = delete;
    Hardware(Hardware&&) = delete;
    Hardware& operator=(const Hardware&) = delete;
    Hardware& operator=(Hardware&&) = delete;

    virtual void init() {
        pinMode(LED_BUILTIN, OUTPUT);
    }
    virtual void initSettings(int nIdx, Settings& settings) {}
    virtual void initRxModule(int nIdx, RxModule& rx) = 0;
    virtual void processStatusFlags(mtime_t ms, uint8_t statusFlags, RssiNode& node) {}
    virtual void resetPairedNode(int pinState) {}
    virtual void doJumpToBootloader() {}
    virtual uint8_t getAddress() { return 0; }
    // value returned by READ_RHFEAT_FLAGS command
    virtual uint16_t getFeatureFlags() { return RHFEAT_NONE; }
    virtual void storeFrequency(uint16_t freq) {}
    virtual void storeEnterAtLevel(rssi_t rssi) {}
    virtual void storeExitAtLevel(rssi_t rssi) {}
    virtual void setStatusLed(bool onFlag)
    {
        if (onFlag)
        {
            if (!currentStatusLedFlag)
            {
                currentStatusLedFlag = true;
                digitalWrite(LED_BUILTIN, ledOnValue);
            }
        }
        else
        {
            if (currentStatusLedFlag)
            {
                currentStatusLedFlag = false;
                digitalWrite(LED_BUILTIN, ledOffValue);
            }
        }
    }
};

extern Hardware& hardware;

#endif
