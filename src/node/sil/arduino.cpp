#include "arduino.h"
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <math.h>

#define ADC_DATA_SIZE 1000

void pinMode(uint8_t pin, uint8_t mode) {

}

void digitalWrite(uint8_t pin, uint8_t val) {

}

static int signal_peak(unsigned long ms, float height, int half_width, int dc) {
    uint16_t t = ms % (8*1024);
    if (t < half_width) {
        return (int) (height*t/half_width + dc);
    } else if (t >= half_width && t < 2*half_width) {
        return (int) (height*(2*half_width-t)/half_width + dc);
    } else {
        return dc;
    }
}

static int signal_wave(unsigned long ms, double freq) {
    return 200*(1.0 + sin(M_2_PI*freq*ms/1000.0 - M_PI_2));
}

static uint32_t startTime;
static int adcDataIndex = 0;
static size_t adcDataCount = 0;
static uint32_t adcDataTime[ADC_DATA_SIZE];
static int adcDataValues[ADC_DATA_SIZE];

int analogRead(uint8_t pin) {
    if (adcDataCount > 0) {
        if (millis()-startTime > adcDataTime[adcDataIndex]-adcDataTime[0] && adcDataIndex < adcDataCount-1) {
            adcDataIndex++;
        }
        return adcDataValues[adcDataIndex];
    } else {
        return signal_peak(millis(), 300.0, 150, 100);
    }
}

unsigned long millis() {
    return micros()/1000;
}

unsigned long micros() {
    static timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return now.tv_sec*1000000 + now.tv_nsec/1000;
}

void delay(unsigned long ms) {
    delayMicroseconds(1000*ms);
}

void delayMicroseconds(unsigned int us) {
    static timespec interval;
    interval.tv_nsec = 1000*us;
    nanosleep(&interval, nullptr);
}

extern void setup();
extern void loop();
extern void serialEvent();

#ifdef _WIN32
static HANDLE hCom;

Stream Serial;

void Stream::bufferRead(const uint8_t data[], size_t size) {
    if (size > buffer.available()) {
        printf("Stream read buffer overflow\n");
    }
    for(int i=0; i<size; i++) {
        buffer.push(data[i]);
    }
}

int Stream::read() {
    return buffer.shift();
}

size_t Stream::write(const uint8_t *buffer, size_t size) {
    DWORD dwBytesWritten;
    if (!WriteFile(hCom, buffer, size, &dwBytesWritten, NULL)) {
        printf("Serial write failed\n");
    }
    return dwBytesWritten;
}

void initSerial(const char* comPort) {
    hCom = CreateFileA(comPort, GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (hCom == INVALID_HANDLE_VALUE) {
        printf("Error opening %s (maybe you meant \\\\.\\%s): %d\n", comPort, comPort, GetLastError());
        hCom = 0;
        return;
    }
    DCB dcb;
    SecureZeroMemory(&dcb, sizeof(DCB));
    dcb.DCBlength = sizeof(DCB);
    if (!GetCommState(hCom, &dcb)) {
        printf("Error getting comm state: %d\n", GetLastError());
        CloseHandle(hCom);
        hCom = 0;
        return;
    }
    dcb.BaudRate = CBR_115200;
    dcb.ByteSize = 8;
    dcb.Parity = NOPARITY;
    dcb.StopBits = ONESTOPBIT;
    if (!SetCommState(hCom, &dcb)) {
        printf("Error setting comm state: %d\n", GetLastError());
        CloseHandle(hCom);
        hCom = 0;
        return;
    }
    COMMTIMEOUTS ctos = {MAXDWORD, 0, 0, 0, 1};
    if (!SetCommTimeouts(hCom, &ctos)) {
        printf("Error setting comm timeouts: %d\n", GetLastError());
        CloseHandle(hCom);
        hCom = 0;
        return;
    }
}

void serial_io() {
    if (hCom) {
        uint8_t buffer[128];
        DWORD dwBytesRead;
        if (!ReadFile(hCom, buffer, sizeof(buffer), &dwBytesRead, NULL)) {
            printf("Serial read failed\n");
        }
        if (dwBytesRead == sizeof(buffer)) {
            printf("Serial read buffer overflow\n");
        }
        Serial.bufferRead(buffer, dwBytesRead);
        for (int i=0; i<dwBytesRead; i++) {
            serialEvent();
        }
    }
}
#else
int Stream::read() {
    return 0;
}

size_t Stream::write(const uint8_t *buffer, size_t size) {
    return 0;
}

void initSerial(const char* comPort) {

}

void serial_io() {

}
#endif

void loadRssiFile(const char* filename) {
    unsigned int t;
    unsigned int rssi;
    FILE *fp = fopen(filename, "r");
    for (adcDataCount = 0; adcDataCount < ADC_DATA_SIZE && fscanf(fp, "%u,%u\n", &t, &rssi) > 0; adcDataCount++) {
        adcDataTime[adcDataCount] = t;
        adcDataValues[adcDataCount] = rssi << 1; // scale-up to original adc value
    }
    fclose(fp);
    adcDataIndex = 0;
}

int main(int argc, const char *argv[])
{
    const char *comPort;
    const char* rssiFile;
    if (argc >= 2) {
        comPort = argv[1];
    } else {
        comPort = nullptr;
    }
    if (argc >= 3) {
        rssiFile = argv[2];
    } else {
        rssiFile = nullptr;
    }
    if (comPort) {
        initSerial(comPort);
    }
    if (rssiFile) {
        loadRssiFile(rssiFile);
    }

    startTime = millis();
    setup();

    unsigned long last_io = 0;
    for (;;) {

        loop();

        unsigned long t = millis();
        if (t - last_io > 5) {
            serial_io();
            last_io = t;
        }
    }

    return 0;
}
