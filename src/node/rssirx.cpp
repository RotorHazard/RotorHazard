#include "clock.h"
#include "rssirx.h"

class SingleRssiReceiver : public RssiReceivers {
private:
    RssiNode node;
    RxModule rx;

public:
    RssiNode& getRssiNode(uint8_t idx) {
      return node;
    };

    RxModule& getRxModule(uint8_t idx) {
      return rx;
    };

    Settings& getSettings(uint8_t idx) {
      return node.getSettings();
    };

    uint8_t getCount() {
      return 1;
    };

    void start() {
      node.start();
    };

    bool readRssi() {
      return node.process(rx.readRssi(), usclock.millis());
    };
};

class VirtualRssiReceivers : public RssiReceivers {
private:
    RssiNode nodes[MULTI_RHNODE_MAX];
    RxModule rx;
    int8_t prevReadIndex = -1;
    uint16_t readCounter = 0;

public:
    RssiNode& getRssiNode(uint8_t idx) {
      return nodes[idx];
    };

    RxModule& getRxModule(uint8_t idx) {
      return rx;
    };

    Settings& getSettings(uint8_t idx) {
      return nodes[idx].getSettings();
    };

    uint8_t getCount() {
      return MULTI_RHNODE_MAX;
    };

    void start() {
      for (int i=0; i<MULTI_RHNODE_MAX; i++) {
        nodes[i].start();
      }
    };

    bool readRssi() {
      // alternate the single rx between different freqs
      uint8_t idx = (readCounter++ % (READS_PER_FREQ*MULTI_RHNODE_MAX))/READS_PER_FREQ;
      if (idx != prevReadIndex) {
        rx.setFrequency(nodes[idx].getSettings().vtxFreq);
        prevReadIndex = idx;
      }
      return nodes[idx].process(rx.readRssi(), usclock.millis());
    };
};

class PhysicalRssiReceivers : public RssiReceivers {
private:
    RssiNode nodes[MULTI_RHNODE_MAX];
    RxModule rxs[MULTI_RHNODE_MAX];

public:
    RssiNode& getRssiNode(uint8_t idx) {
      return nodes[idx];
    };

    RxModule& getRxModule(uint8_t idx) {
      return rxs[idx];
    };

    Settings& getSettings(uint8_t idx) {
      return nodes[idx].getSettings();
    };

    uint8_t getCount() {
      return MULTI_RHNODE_MAX;
    };

    void start() {
      for (int i=0; i<MULTI_RHNODE_MAX; i++) {
        nodes[i].start();
      }
    };

    bool readRssi() {
      bool crossingFlag;
      for (int i=0; i<MULTI_RHNODE_MAX; i++) {
        if (nodes[i].process(rxs[i].readRssi(), usclock.millis())) {
          crossingFlag = true;
        }
      }
      return crossingFlag;
    };
};

#if MULTI_RHNODE_MAX == 1
SingleRssiReceiver defaultRssiReceivers;
#else
VirtualRssiReceivers defaultRssiReceivers;
#endif
RssiReceivers *RssiReceivers::rssiRxs = &defaultRssiReceivers;
