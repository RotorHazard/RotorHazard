#include "config.h"
#include "commands.h"

#ifdef USE_WIFI
#if TARGET == ESP32_TARGET
#include <WiFi.h>
#include <HTTPUpdate.h>
#elif TARGET == ESP8266_TARGET
#include <ESP8266WiFi.h>
#include <ESP8266httpUpdate.h>
#endif

static WiFiClient wifiClient;
static Message wifiMessage;

void wifiInit() {
    WiFi.setHostname(WIFI_HOSTNAME);
    WiFi.enableSTA(true);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    WiFi.waitForConnectResult();
    WiFiClient otaClient;
#if TARGET == ESP32_TARGET
    httpUpdate.update(otaClient, OTA_URL, FIRMWARE_VERSION);
#elif TARGET == ESP8266_TARGET
    ESPhttpUpdate.update(otaClient, OTA_URL, FIRMWARE_VERSION);
#endif
}

void wifiEvent() {
    handleStreamEvent(wifiClient, wifiMessage, WIFI_SOURCE);
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
