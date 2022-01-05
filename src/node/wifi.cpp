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

#ifdef WIFI_SERVER
static WiFiClient wifiClient;
static Message wifiMessage;
#endif

#ifdef USE_MQTT
#include "mqtt.h"
static WiFiClient mqttWifiClient;
#endif

void wifiInit() {
    WiFi.setHostname(WIFI_HOSTNAME);
    WiFi.enableSTA(true);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    WiFi.waitForConnectResult();

#ifdef OTA_URL
    WiFiClient otaClient;
#if TARGET == ESP32_TARGET
    httpUpdate.update(otaClient, OTA_URL, FIRMWARE_VERSION);
#elif TARGET == ESP8266_TARGET
    ESPhttpUpdate.update(otaClient, OTA_URL, FIRMWARE_VERSION);
#endif
#endif

#ifdef WIFI_SERVER
    wifiClient.setNoDelay(true);
#endif

#ifdef USE_MQTT
    mqttInit(mqttWifiClient);
#endif
}

#ifdef WIFI_SERVER
void wifiEvent() {
    handleStreamEvent(wifiClient, wifiMessage, WIFI_SOURCE);
}
#endif

void wifiEventRun() {
#ifdef WIFI_SERVER
    if (wifiClient.connected()) {
        if (wifiClient.available()) {
            wifiEvent();
        }
    } else {
        wifiClient.connect(WIFI_SERVER, WIFI_PORT);
    }
#endif

#ifdef USE_MQTT
    mqttEventRun();
#endif
}
#endif
