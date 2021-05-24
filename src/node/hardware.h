#ifndef hardware_h
#define hardware_h

#include "rssi.h"
#include "rx.h"

// features flags for value returned by READ_RHFEAT_FLAGS command
#define RHFEAT_STM32_MODE ((uint16_t)0x0004)      // STM 32-bit processor running multiple nodes
#define RHFEAT_JUMPTO_BOOTLDR ((uint16_t)0x0008)  // JUMP_TO_BOOTLOADER command supported
#define RHFEAT_IAP_FIRMWARE ((uint16_t)0x0010)    // in-application programming of firmware supported
#define RHFEAT_PH ((uint16_t)0x0100)    // in-application programming of firmware supported
#define RHFEAT_NONE ((uint16_t)0)

// dummy macro
#define LOG_ERROR(...)

class Hardware {
private:
    const uint8_t ledOnValue, ledOffValue;

protected:
#ifdef LED_BUILTIN
    bool currentStatusLedFlag = false;
#endif

public:
    Hardware(uint8_t ledOn, uint8_t ledOff) : ledOnValue(ledOn), ledOffValue(ledOff) {
    }
    Hardware(const Hardware&) = delete;
    Hardware(Hardware&&) = delete;
    Hardware& operator=(const Hardware&) = delete;
    Hardware& operator=(Hardware&&) = delete;

    virtual void init() {
#ifdef LED_BUILTIN
        pinMode(LED_BUILTIN, OUTPUT);
#endif
    }
    virtual void initSettings(uint_fast8_t nIdx, Settings& settings) {}
    virtual void initRxModule(uint_fast8_t nIdx, RxModule& rx) = 0;
    virtual void processStatusFlags(mtime_t ms, uint8_t statusFlags) {}
    /**
     * Reads a 3.3V signal from an ADC as an 8-bit value.
     * Assumes a 10-bit ADC with a 5V range.
     */
    virtual uint8_t readADC(uint8_t pin) {
        // reads 5V value as 0-1023, RX5808 is 3.3V powered so RSSI pin will never output the full range
        int raw = analogRead(pin);
        // clamp upper range to fit scaling
        if (raw > 0x01FF) {
            raw = 0x01FF;
        }
        // rescale to fit into a byte and remove some jitter
        return raw >> 1;
    }
    virtual void resetPairedNode(bool pinState) {}
    virtual void doJumpToBootloader() {}
    virtual uint8_t getAddress() { return 0; }
    virtual const char* getProcessorType() = 0;
    // value returned by READ_RHFEAT_FLAGS command
    virtual uint16_t getFeatureFlags() {
#ifdef USE_PH
        return RHFEAT_PH;
#else
        return RHFEAT_NONE;
#endif
    }
    virtual void storeFrequency(freq_t freq) {}
    virtual void storeEnterAtLevel(rssi_t rssi) {}
    virtual void storeExitAtLevel(rssi_t rssi) {}
    virtual void setStatusLed(bool onFlag) {
#ifdef LED_BUILTIN
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
#endif
    }
};

extern Hardware& hardware;

#endif
