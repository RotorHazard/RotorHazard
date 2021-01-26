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
    void initRxModule(int nIdx, RxModule& rx)
    {
        printf("Initializing RX module %d\n", nIdx);
        isRxInit[nIdx] = true;
    }
    void initSettings(int nIdx, Settings& settings)
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
};

extern TestHardware testHardware;
extern Hardware *hardware;
