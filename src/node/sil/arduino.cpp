#include "arduino.h"
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <math.h>

void pinMode(uint8_t pin, uint8_t mode) {

}

void digitalWrite(uint8_t pin, uint8_t val) {

}

int analogRead(uint8_t pin) {
    double t = millis()/100.0;
    return (int) abs(250*sin(t/8)+100*cos(t/2)+50*sin(t)+25*cos(2*t));
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

size_t Stream::write(const uint8_t *buffer, size_t size) {
    DWORD dwBytesWritten;
    if (!WriteFile(hCom, buffer, size, &dwBytesWritten, NULL)) {
        printf("Serial write failed\n");
    }
    return dwBytesWritten;
}

void init(const char* comPort) {
    if (comPort) {
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
}

void serial_io() {
    if (hCom) {
        DWORD dwBytesRead;
        if (!ReadFile(hCom, &Serial.byteRead, 1, &dwBytesRead, NULL)) {
            printf("Serial read failed\n");
        }
        if (dwBytesRead > 0) {
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

void init(const char* comPort) {

}

void serial_io() {

}
#endif

int main(int argc, const char *argv[])
{
    const char *comPort;
    if (argc == 2) {
        comPort = argv[1];
    } else {
        comPort = nullptr;
    }
    init(comPort);
    setup();
    for (;;) {
        loop();
        serial_io();
    }

    return 0;
}
