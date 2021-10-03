#include <stdio.h>
#include "../hardware.h"

class SILHardware : public Hardware {
public:
    SILHardware() : Hardware(HIGH,LOW) {
    }
    void init()
    {
        Hardware::init();
#ifdef _WIN32
        HANDLE hStdOut = GetStdHandle(STD_OUTPUT_HANDLE);
        DWORD consoleMode;
        GetConsoleMode(hStdOut, &consoleMode);
        consoleMode |= ENABLE_VIRTUAL_TERMINAL_PROCESSING;
        SetConsoleMode(hStdOut, consoleMode);
#endif
        printf("Hardware initialized\n");
    }
    void initRxModule(uint_fast8_t nIdx, RxModule& rx)
    {
        uint8_t dataPin = MOSI;
        uint8_t clkPin = SCK;
        uint8_t selPin = 41 + nIdx;
        uint8_t rssiPin = 61 + nIdx;
        printf("Initializing RX module %d with SPI pins: data=%u, clock=%u, chip-select=%u\n", nIdx, dataPin, clkPin, selPin);
        rx.init(dataPin, clkPin, selPin, rssiPin);
    }
    void initSettings(uint_fast8_t nIdx, Settings& settings)
    {
        printf("Initializing settings for RX module %d\n", nIdx);
    }
    void setStatusLed(bool onFlag) {
        bool currentFlag = currentStatusLedFlag;
        Hardware::setStatusLed(onFlag);
        if (onFlag != currentFlag) {
            if (onFlag) {
                printf("\e[1G\e[1;31m * ");
            } else {
                printf("\e[2K");
            }
            printf("\e[0m");
        }
    }
    const char* getProcessorType() {
        return "Host";
    }
};
