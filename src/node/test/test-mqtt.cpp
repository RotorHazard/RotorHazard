#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "../rssirx.h"
#include "../mqtt.h"

unittest(mqtt_freq)
{
    mqttProcessMessage("node_managers/timer/wifi-node-1/0/frequency", "5555", 4);
    Settings& settings = rssiRxs.getSettings(0);
    assertEqual(5555, settings.vtxFreq);
    assertTrue(rssiRxs.getRssiNode(0).active);
    assertFalse(rssiRxs.getRxModule(0).isPoweredDown());
}

unittest(mqtt_power)
{
    mqttProcessMessage("node_managers/timer/wifi-node-1/0/power", "0", 1);
    Settings& settings = rssiRxs.getSettings(0);
    assertFalse(rssiRxs.getRssiNode(0).active);
    assertTrue(rssiRxs.getRxModule(0).isPoweredDown());
}

unittest_main()
