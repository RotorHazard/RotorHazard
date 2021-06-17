#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssirx.h"

#define assertRssiRx(rssirx, numRxs) \
{ \
    assertEqual(numRxs, rssirx.getCount()); \
    for (int i=0; i<rssirx.getCount(); i++) { \
        rssirx.getRssiNode(i); \
        rssirx.getRxModule(i); \
        rssirx.getSettings(i); \
        assertEqual(i, rssirx.getSlotIndex(i)); \
    } \
    rssirx.start(0, usclock); \
    assertFalse(rssirx.readRssi(0, usclock)); \
}

unittest(single_rx)
{
    SingleRssiReceiver<RX_IMPL> rssirx;
    assertRssiRx(rssirx, 1);
}

unittest(physical_rx_0)
{
    PhysicalRssiReceivers<RX_IMPL,0> rssirx;
    assertRssiRx(rssirx, 0);
}

unittest(physical_rx_2)
{
    PhysicalRssiReceivers<RX_IMPL,2> rssirx;
    assertRssiRx(rssirx, 2);
}

unittest(virtual_rx_0)
{
    VirtualRssiReceivers<RX_IMPL,0> rssirx;
    assertRssiRx(rssirx, 0);
}

unittest(virtual_rx_2)
{
    VirtualRssiReceivers<RX_IMPL,2> rssirx;
    assertRssiRx(rssirx, 2);
}

unittest_main()
