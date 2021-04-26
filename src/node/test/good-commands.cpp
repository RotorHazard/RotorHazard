#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "commands.h"

extern void setup();
extern void loop();
extern void serialEvent();

uint16_t read16(String& s, int i) {
    uint8_t b1 = s[i++];
    uint8_t b2 = s[i++];
    return (b1 << 8) | b2;
}

void setChecksum(char data[], int len) {
    uint8_t checksum = 0;
    for (int i=1; i<len-1; i++)
    {
        checksum += (uint8_t) data[i];
    }
    data[len-1] = checksum;
}

void sendData(GodmodeState* state, const char data[], int len, Message& msg) {
    static char szData[32];
    memcpy(szData, data, len);
    szData[len] = '\0';
    state->serialPort[0].dataIn = String(szData);
    for (int i=0; i<len; i++) {
        handleStreamEvent(Serial, msg);
    }
}

unittest(command_freq)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    Message serialMessage;
    setup();
    const char cmd[] = {READ_FREQUENCY};
    sendData(nano, cmd, sizeof(cmd), serialMessage);
    assertEqual(3, nano->serialPort[0].dataOut.length());
    assertEqual(5800, read16(nano->serialPort[0].dataOut, 0));
}

unittest(command_scan)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    Message serialMessage;
    setup();
    assertEqual(false, rssiRxs.getRssiNode(0).active);
    assertEqual(0, rssiRxs.getRssiNode(0).getSettings().mode);
    char modeCmd[] = {WRITE_MODE, 1, 0};
    setChecksum(modeCmd, sizeof(modeCmd));
    sendData(nano, modeCmd, sizeof(modeCmd), serialMessage);
    assertEqual(1, rssiRxs.getRssiNode(0).getSettings().mode);
    assertEqual(MIN_SCAN_FREQ, rssiRxs.getRssiNode(0).getSettings().vtxFreq);
    // wait for some frequency changes
    for (int i=0; i<100; i++) {
        loop();
        nano->micros += 1000;
    }
    assertEqual(true, rssiRxs.getRssiNode(0).active);
    assertEqual(4, (int)rssiRxs.getRssiNode(0).scanHistory.size());
    char readCmd[] = {READ_NODE_SCAN_HISTORY};
    sendData(nano, readCmd, sizeof(readCmd), serialMessage);
    assertEqual(10, nano->serialPort[0].dataOut.length());
    assertEqual(1, (int)rssiRxs.getRssiNode(0).scanHistory.size());
    assertEqual(MIN_SCAN_FREQ, read16(nano->serialPort[0].dataOut, 0));
    assertEqual(MIN_SCAN_FREQ+SCAN_FREQ_INCR, read16(nano->serialPort[0].dataOut, 3));
    assertEqual(MIN_SCAN_FREQ+2*SCAN_FREQ_INCR, read16(nano->serialPort[0].dataOut, 6));
}

unittest_main()
