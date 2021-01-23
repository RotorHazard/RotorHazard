#include "microclock.h"
#include "rssirx.h"

#define MIN_RSSI_DETECT 5 //value for detecting node as installed

#if !STM32_MODE_FLAG
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
    uint8_t nodeCount = MULTI_RHNODE_MAX;
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
      return nodeCount;
    };

    void start() {
      for (int i=0; i<nodeCount; i++) {
        nodes[i].start();
      }
    };

    bool readRssi() {
      uint8_t idx;
      if (nodeCount > 1) {
          // alternate the single rx between different freqs
          idx = (readCounter++ % (READS_PER_FREQ*nodeCount))/READS_PER_FREQ;
          if (idx != prevReadIndex) {
            rx.setFrequency(nodes[idx].getSettings().vtxFreq);
            prevReadIndex = idx;
          }
      } else {
          idx = 0;
      }
      return nodes[idx].process(rx.readRssi(), usclock.millis());
    };
};
#endif

class PhysicalRssiReceivers : public RssiReceivers {
private:
    uint8_t nodeCount = MULTI_RHNODE_MAX;
    uint8_t nodeToSlot[MULTI_RHNODE_MAX];
    RssiNode nodes[MULTI_RHNODE_MAX];
    RxModule rxs[MULTI_RHNODE_MAX];

public:
    RssiNode& getRssiNode(uint8_t idx) {
      return nodes[nodeToSlot[idx]];
    };

    RxModule& getRxModule(uint8_t idx) {
      return rxs[nodeToSlot[idx]];
    };

    Settings& getSettings(uint8_t idx) {
      return nodes[nodeToSlot[idx]].getSettings();
    };

    uint8_t getSlotIndex(uint8_t idx) { return nodeToSlot[idx]; };

    uint8_t getCount() {
      return nodeCount;
    };

    void start() {
      int sIdx=0;
      for (int nIdx=0; nIdx<nodeCount; nIdx++) {
          if (rxs[nIdx].readRssi() > MIN_RSSI_DETECT) {
              nodeToSlot[sIdx++] = nIdx;
          }
      }
      nodeCount = sIdx;

      for (int i=0; i<getCount(); i++) {
        getRssiNode(i).start();
      }
    };

    bool readRssi() {
      bool crossingFlag;
      for (int i=0; i<getCount(); i++) {
        if (getRssiNode(i).process(getRxModule(i).readRssi(), usclock.millis())) {
          crossingFlag = true;
        }
      }
      return crossingFlag;
    };
};

#if STM32_MODE_FLAG
    PhysicalRssiReceivers defaultRssiReceivers;
#else
    #if MULTI_RHNODE_MAX == 1
    SingleRssiReceiver defaultRssiReceivers;
    #else
    VirtualRssiReceivers defaultRssiReceivers;
    #endif
#endif
RssiReceivers *const RssiReceivers::rssiRxs = &defaultRssiReceivers;
