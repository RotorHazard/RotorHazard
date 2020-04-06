// Pin to reset paired Arduino via command for ISP
#if !ARDUVIDRX_WIRING_FLAG
#define NODE_RESET_PIN 12
#else
#define NODE_RESET_PIN 13
#endif

void initNodeResetPin();
void resetPairedNode(int pinState);
