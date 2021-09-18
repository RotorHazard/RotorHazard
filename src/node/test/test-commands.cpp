#include <ArduinoUnitTests.h>
#include <Godmode.h>
#include "commands.h"

extern void setup();
extern void loop();
extern void serialEvent();

void write16(char data[], int i, uint16_t v) {
    data[i++] = (v >> 8);
    data[i++] = v;
}

uint8_t read8(String& s, int i) {
    return s[i];
}

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
        handleStreamEvent(Serial, msg, SERIAL_SOURCE);
    }
}

unittest(command_getPayloadSize)
{
    Message serialMessage;
    assertEqual(-1, serialMessage.getPayloadSize());
}

unittest(command_enterAtLevel)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    Message serialMessage;
    setup();
    uint8_t newLevel = 59;

    char setCmd[] = {WRITE_ENTER_AT_LEVEL, (char)newLevel, 0};
    setChecksum(setCmd, sizeof(setCmd));
    sendData(nano, setCmd, sizeof(setCmd), serialMessage);
    Settings& settings = rssiRxs.getSettings(0);
    assertEqual(newLevel, settings.enterAtLevel);

    const char readCmd[] = {READ_ENTER_AT_LEVEL};
    sendData(nano, readCmd, sizeof(readCmd), serialMessage);
    assertEqual(2, nano->serialPort[0].dataOut.length());
    assertEqual(newLevel, read8(nano->serialPort[0].dataOut, 0));
}

unittest(command_exitAtLevel)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    Message serialMessage;
    setup();
    uint8_t newLevel = 49;

    char setCmd[] = {WRITE_EXIT_AT_LEVEL, (char)newLevel, 0};
    setChecksum(setCmd, sizeof(setCmd));
    sendData(nano, setCmd, sizeof(setCmd), serialMessage);
    Settings& settings = rssiRxs.getSettings(0);
    assertEqual(newLevel, settings.exitAtLevel);

    const char readCmd[] = {READ_EXIT_AT_LEVEL};
    sendData(nano, readCmd, sizeof(readCmd), serialMessage);
    assertEqual(2, nano->serialPort[0].dataOut.length());
    assertEqual(newLevel, read8(nano->serialPort[0].dataOut, 0));
}

unittest(command_freq)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    Message serialMessage;
    setup();
    freq_t newFreq = 5808;

    char freqCmd[] = {WRITE_FREQUENCY, 0, 0, 0};
    write16(freqCmd, 1, newFreq);
    setChecksum(freqCmd, sizeof(freqCmd));
    sendData(nano, freqCmd, sizeof(freqCmd), serialMessage);
    Settings& settings = rssiRxs.getSettings(0);
    assertEqual(newFreq, settings.vtxFreq);

    const char readCmd[] = {READ_FREQUENCY};
    sendData(nano, readCmd, sizeof(readCmd), serialMessage);
    assertEqual(3, nano->serialPort[0].dataOut.length());
    assertEqual(newFreq, read16(nano->serialPort[0].dataOut, 0));
}

unittest(command_nodeIndex)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    Message serialMessage;
    setup();
    uint8_t newNode = 0;

    char nodeCmd[] = {WRITE_CURNODE_INDEX, (char)newNode, 0};
    setChecksum(nodeCmd, sizeof(nodeCmd));
    sendData(nano, nodeCmd, sizeof(nodeCmd), serialMessage);
    assertEqual(newNode, cmdRssiNodeIndex);

    const char readCmd[] = {READ_CURNODE_INDEX};
    sendData(nano, readCmd, sizeof(readCmd), serialMessage);
    assertEqual(2, nano->serialPort[0].dataOut.length());
    assertEqual(newNode, read8(nano->serialPort[0].dataOut, 0));
}

unittest(command_nodeIndex_invalid)
{
    GodmodeState* nano = GODMODE();
    nano->reset();
    Message serialMessage;
    setup();
    uint8_t newNode = 10;

    char nodeCmd[] = {WRITE_CURNODE_INDEX, (char)newNode, 0};
    setChecksum(nodeCmd, sizeof(nodeCmd));
    sendData(nano, nodeCmd, sizeof(nodeCmd), serialMessage);
    assertEqual(0, cmdRssiNodeIndex);
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
    for (int i=0; i<200; i++) {
        loop();
        nano->micros += 1000;
    }
    assertEqual(true, rssiRxs.getRssiNode(0).active);
    assertEqual(4, (int)rssiRxs.getRssiNode(0).scanHistory.size());

    const char readCmd[] = {READ_NODE_SCAN_HISTORY};
    sendData(nano, readCmd, sizeof(readCmd), serialMessage);
    assertEqual(10, nano->serialPort[0].dataOut.length());
    assertEqual(1, (int)rssiRxs.getRssiNode(0).scanHistory.size());
    assertEqual(MIN_SCAN_FREQ, read16(nano->serialPort[0].dataOut, 0));
    assertEqual(MIN_SCAN_FREQ+SCAN_FREQ_INCR, read16(nano->serialPort[0].dataOut, 3));
    assertEqual(MIN_SCAN_FREQ+2*SCAN_FREQ_INCR, read16(nano->serialPort[0].dataOut, 6));
}

unittest_main()
