#ifndef mqtt_h
#define mqtt_h

#include <Client.h>
#include "rssi.h"

void mqttInit(Client& client);
void mqttEventRun();
void mqttPublish(RssiNode& rssiNode, const char subTopic[], const char msg[], int msgLen);

int sprints(char* dest, const char* src);

#ifdef __TEST__
void mqttProcessMessage(const char topic[], const char msg[], int msgLen);
#endif

#endif
