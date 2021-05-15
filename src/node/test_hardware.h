#include "hardware.h"

class TestHardware : public Hardware {
public:
    bool isInit;
    bool isRxInit[MULTI_RHNODE_MAX];
    bool isSettingsInit[MULTI_RHNODE_MAX];

    TestHardware() : Hardware(HIGH,LOW) {
    }
    void init()
    {
        Hardware::init();
        printf("Hardware initialized\n");
        isInit = true;
    }
    void initRxModule(uint_fast8_t nIdx, RxModule& rx)
    {
        printf("Initializing RX module %d\n", nIdx);
        isRxInit[nIdx] = true;
    }
    void initSettings(uint_fast8_t nIdx, Settings& settings)
    {
        printf("Initializing settings for RX module %d\n", nIdx);
        isSettingsInit[nIdx] = true;
    }
    void setStatusLed(bool onFlag) {
        bool currentFlag = currentStatusLedFlag;
        Hardware::setStatusLed(onFlag);
        if (onFlag != currentFlag) {
            printf("Status LED changed to %d\n", onFlag);
        }
    }

    const char* getProcessorType() {
      return "Test";
    }
};

extern TestHardware testHardware;
