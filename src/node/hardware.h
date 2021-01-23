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
    bool currentStatusLedFlag = false;

public:
    Hardware(uint8_t ledOn, uint8_t ledOff) : ledOnValue(ledOn), ledOffValue(ledOff) {
    };
    void init() {
        pinMode(LED_BUILTIN, OUTPUT);
    };
    void initSettings(int nIdx, Settings& settings) {};
    virtual void initRxModule(int nIdx, RxModule& rx) = 0;
    void processStatusFlags(uint8_t statusFlags, RssiNode& node) {};
    void resetPairedNode(int pinState) {};
    void doJumpToBootloader() {};
    uint8_t getAddress() { return 0; };
    // value returned by READ_RHFEAT_FLAGS command
    uint16_t getFeatureFlags() { return RHFEAT_NONE; };
    void storeFrequency(uint16_t freq) {};
    void storeEnterAtLevel(rssi_t rssi) {};
    void storeExitAtLevel(rssi_t rssi) {};
    void setStatusLed(bool onFlag)
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

#endif
