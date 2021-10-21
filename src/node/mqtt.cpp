#include "config.h"

#ifdef USE_MQTT
#include "rssirx.h"
#include "mqtt.h"
#include "hardware.h"

static int sprintNodeTopic(char* dest);

#ifndef __TEST__
#include <MQTT.h>

static void mqttMessageReceived(MQTTClient *client, char topic[], char msg[], int msgLen);
static void mqttProcessMessage(const char topic[], const char msg[], int msgLen);

static MQTTClient mqttClient(256);

void mqttInit(Client& client) {
    mqttClient.begin(MQTT_BROKER, MQTT_PORT, client);
    mqttClient.onMessageAdvanced(mqttMessageReceived);
}

void mqttEventRun() {
    if (mqttClient.loop()) {
#if TARGET == ESP8266_TARGET
        delay(10); // as per notes @ https://github.com/256dpi/arduino-mqtt
#endif
    } else {
        if (mqttClient.connect(WIFI_HOSTNAME, MQTT_USERNAME, MQTT_PASSWORD)) {
            char nodeTopicFilter[64] = "";
            int n = sprintNodeTopic(nodeTopicFilter);
            sprints(nodeTopicFilter+n, "/+/frequency");
            mqttClient.subscribe(nodeTopicFilter);
            sprints(nodeTopicFilter+n, "/+/power");
            mqttClient.subscribe(nodeTopicFilter);
        }
    }
}

static int findNodeIndex(RssiNode& rssiNode) {
    for (int_fast8_t i=rssiRxs.getCount()-1; i>=0; i--) {
        if (&rssiRxs.getRssiNode(i) == &rssiNode) {
            return i;
        }
    }
    return -1;
}

void mqttPublish(RssiNode& rssiNode, const char subTopic[], const char msg[], int msgLen) {
    int idx = findNodeIndex(rssiNode);
    if (idx >= 0) {
        char topic[128] = "";
        int n = sprintNodeTopic(topic);
        n += sprints(topic+n, "/");
        itoa(idx, topic+n, 10);
        n += strlen(topic+n);
        n += sprints(topic+n, "/");
        n += sprints(topic+n, subTopic);
        mqttClient.publish(topic, msg, msgLen);
    }
}

void mqttMessageReceived(MQTTClient *client, char topic[], char msg[], int msgLen) {
    mqttProcessMessage(topic, msg, msgLen);
}
#else
// test stub
void mqttPublish(RssiNode& rssiNode, const char subTopic[], const char msg[], int msgLen) {
}
#endif


constexpr int maxIdxDigits = 2;
constexpr int maxFreqDigits = 4;

inline bool copyNonNegativeInteger(char* dst, const char* src, int maxLen);

/**
 * Topic structure:
 * node_manager/<name>/<idx>/frequency
 * node_manager/<name>/<idx>/power
 */
void mqttProcessMessage(const char topic[], const char msg[], int msgLen) {
    char homeTopic[64] = "";
    int n = sprintNodeTopic(homeTopic);
    if (strncmp(topic, homeTopic, n) == 0) {
        // definitely for us
        if (strncmp(topic+n, "/", 1) == 0) {
            // vrx specific
            n += 1;
            const char* startIdxPtr = topic + n;
            const char* endIdxPtr = strchr(startIdxPtr, '/');
            if (!endIdxPtr) {
                endIdxPtr = startIdxPtr + strlen(startIdxPtr);
            }
            int idxLen = endIdxPtr - startIdxPtr;
            char szIdx[maxIdxDigits+1];
            if (idxLen <= maxIdxDigits && copyNonNegativeInteger(szIdx, startIdxPtr, idxLen)) {
                int nodeIdx = atoi(szIdx);
                RssiNode& rssiNode = rssiRxs.getRssiNode(nodeIdx);
                RxModule& rx = rssiRxs.getRxModule(nodeIdx);
                if (strcmp(endIdxPtr, "/frequency") == 0) {
                    char szFreq[maxFreqDigits+1];
                    if (msgLen <= maxFreqDigits && copyNonNegativeInteger(szFreq, msg, msgLen)) {
                        freq_t freq = atol(szFreq);
                        Settings& settings = rssiNode.getSettings();
                        if (freq != settings.vtxFreq)
                        {
                            settings.vtxFreq = freq;
                            hardware.storeFrequency(freq);
                            rssiNode.resetState(usclock.millis());  // restart rssi peak tracking for node
                        }
                        if (rx.isPoweredDown()) {
                            rx.reset();
                        }
                        rx.setFrequency(freq);
                        rssiNode.active = true;
                    }
                } else if (strcmp(endIdxPtr, "/power") == 0) {
                    if (msgLen == 1 && msg[0] == '1' && rx.isPoweredDown()) {
                        rx.reset();
                        rssiNode.resetState(usclock.millis());  // restart rssi peak tracking for node
                        rssiNode.active = true;
                    } else if (msgLen == 1 && msg[0] == '0' && !rx.isPoweredDown()) {
                        rx.powerDown();
                        rssiNode.active = false;
                    }
                }
            }
        }
    }
}

int sprintNodeTopic(char* dest) {
    int n = sprints(dest, MQTT_TOPIC);
    dest[n++] = '/';
    n += sprints(dest+n, WIFI_HOSTNAME);
    return n;
}

bool copyNonNegativeInteger(char* dst, const char* src, int len) {
    int i = 0;
    for (; i<len; i++) {
        if (isdigit(src[i])) {
            dst[i] = src[i];
        } else {
            return false;
        }
    }
    dst[i] = '\0';
    return true;
}


int sprints(char* dest, const char* src) {
  strcpy(dest, src);
  return strlen(src);
}

#endif
