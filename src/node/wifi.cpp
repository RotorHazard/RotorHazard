#include "config.h"
#include "commands.h"

#ifdef USE_WIFI
#if TARGET == ESP32_TARGET
#include <WiFi.h>
#elif TARGET == ESP8266_TARGET
#include <ESP8266WiFi.h>
#endif

static WiFiClient wifiClient;
static Message wifiMessage;

void wifiInit() {
    WiFi.setHostname(WIFI_HOSTNAME);
    WiFi.enableSTA(true);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void wifiEvent() {
    handleStreamEvent(wifiClient, wifiMessage);
}

void wifiEventRun() {
    if (wifiClient.connected()) {
        if (wifiClient.available()) {
            wifiEvent();
        }
    } else {
        wifiClient.connect(WIFI_SERVER, WIFI_PORT);
    }
}
#endif
