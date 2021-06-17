#include "rssirx.h"

#if TARGET == STM32_TARGET || TARGET == ESP32_TARGET
    PhysicalRssiReceivers<RX_IMPL,MULTI_RHNODE_MAX> defaultRssiReceivers;
#else
    #if MULTI_RHNODE_MAX == 1
    SingleRssiReceiver<RX_IMPL> defaultRssiReceivers;
    #else
    VirtualRssiReceivers<RX_IMPL,MULTI_RHNODE_MAX> defaultRssiReceivers;
    #endif
#endif
RssiReceivers& rssiRxs = defaultRssiReceivers;
