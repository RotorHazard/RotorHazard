#include "arduino.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <signal.h>

constexpr size_t ADC_DATA_SIZE = 1000;

void pinMode(uint8_t pin, uint8_t mode) {

}

void digitalWrite(uint8_t pin, uint8_t val) {

}

enum ClockType {REALTIME, COUNTER};
static ClockType adcSignalClock = REALTIME;

static int signal_peak(unsigned long ms, float height, int half_width, int dc) {
    uint16_t period = 8*1024;
    if (adcSignalClock == COUNTER) {
        half_width = 10;
        period = 3*half_width;
    }
    uint16_t t = ms % period;
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
    int value = 0;
    if (adcDataCount > 0) {
        if (adcDataIndex < adcDataCount) {
            if (adcSignalClock == REALTIME) {
                unsigned long t = millis();
                if (t-startTime > adcDataTime[adcDataIndex]-adcDataTime[0]) {
                    adcDataIndex++;
                }
                value = adcDataValues[adcDataIndex];
            } else {
                value = adcDataValues[adcDataIndex++];
            }
        }
    } else {
        unsigned long t;
        if (adcSignalClock == REALTIME) {
            t = millis();
        } else {
            t = adcDataIndex++;
        }
        value = signal_peak(t, 300.0, 150, 100);
    }
    return value;
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

Stream Serial;

int Stream::read() {
    return buffer.shift();
}

void Stream::copyToBuffer(const uint8_t data[], size_t size) {
    if (size > buffer.available()) {
        fprintf(stderr, "Stream read buffer overflow\n");
    }
    for(int i=0; i<size; i++) {
        buffer.push(data[i]);
    }
}

#ifdef _WIN32
static HANDLE hCom = 0;

size_t Stream::write(const uint8_t* buffer, size_t size) {
    DWORD dwBytesWritten;
    if (!WriteFile(hCom, buffer, size, &dwBytesWritten, NULL)) {
        fprintf(stderr, "Serial write failed\n");
    }
    return dwBytesWritten;
}

void closeSerial() {
    if (hCom > 0) {
        CloseHandle(hCom);
        hCom = 0;
    }
}

void initSerial(const char* comPort) {
    hCom = CreateFileA(comPort, GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (hCom == INVALID_HANDLE_VALUE) {
        fprintf(stderr, "Error opening %s (maybe you meant \\\\.\\%s): %d\n", comPort, comPort, GetLastError());
        return;
    }
    DCB dcb;
    SecureZeroMemory(&dcb, sizeof(DCB));
    dcb.DCBlength = sizeof(DCB);
    if (!GetCommState(hCom, &dcb)) {
        fprintf(stderr, "Error getting comm state: %d\n", GetLastError());
        closeSerial();
        return;
    }
    dcb.BaudRate = CBR_115200;
    dcb.ByteSize = 8;
    dcb.Parity = NOPARITY;
    dcb.StopBits = ONESTOPBIT;
    if (!SetCommState(hCom, &dcb)) {
        fprintf(stderr, "Error setting comm state: %d\n", GetLastError());
        closeSerial();
        return;
    }
    COMMTIMEOUTS ctos = {MAXDWORD, 0, 0, 0, 1};
    if (!SetCommTimeouts(hCom, &ctos)) {
        fprintf(stderr, "Error setting comm timeouts: %d\n", GetLastError());
        closeSerial();
        return;
    }

    fprintf(stderr, "Opened %s\n", comPort);
}

void perform_io() {
    if (hCom) {
        uint8_t buffer[128];
        DWORD dwBytesRead;
        if (!ReadFile(hCom, buffer, sizeof(buffer), &dwBytesRead, NULL)) {
            fprintf(stderr, "Serial read failed\n");
        }
        if (dwBytesRead == sizeof(buffer)) {
            fprintf(stderr, "Serial read buffer overflow\n");
        }
        Serial.copyToBuffer(buffer, dwBytesRead);
        for (int i=0; i<dwBytesRead; i++) {
            serialEvent();
        }
    }
}
#else
static int sockfd = 0;

size_t Stream::write(const uint8_t* buffer, size_t size) {
    ssize_t bytesWritten = ::write(sockfd, buffer, size);
    if (bytesWritten < 0) {
        fprintf(stderr, "Socket write failed\n");
    }
    return bytesWritten;
}

void closeSocket() {
    if (sockfd > 0) {
        close(sockfd);
        sockfd = 0;
    }
}

void initSocket(const char* host, int port) {
    struct hostent* hostinfo = gethostbyname(host);
    if (hostinfo == nullptr) {
        fprintf(stderr, "Unknown host %s\n", host);
        return;
    }

    sockaddr_in sock_addr;
    sock_addr.sin_family = AF_INET;
    sock_addr.sin_port = htons(port);
    sock_addr.sin_addr.s_addr = *(uint32_t*) (hostinfo->h_addr);

    sockfd = socket(PF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        fprintf(stderr, "Failed to create socket\n");
        return;
    }

    bool connected = false;
    int numRetries = 30;
    for (int i=0; i<numRetries; i++) {
        connected = (connect(sockfd, (struct sockaddr *) &sock_addr, sizeof(sock_addr)) == 0);
        if (connected) {
            break;
        }
        sleep(1);
    }
    if (!connected) {
        fprintf(stderr, "Failed to connect to %s:%d\n", host, port);
        closeSocket();
        return;
    }

    fprintf(stderr, "Connected to %s:%d\n", host, port);
}

void perform_io() {
    if (sockfd > 0) {
        uint8_t buffer[128];
        ssize_t bytesRead = read(sockfd, buffer, sizeof(buffer));
        if (bytesRead < 0) {
            fprintf(stderr, "Socket read failed\n");
        }
        if (bytesRead == sizeof(buffer)) {
            fprintf(stderr, "Socket read buffer overflow\n");
        }
        Serial.copyToBuffer(buffer, bytesRead);
        for (int i=0; i<bytesRead; i++) {
            serialEvent();
        }
    }
}
#endif

void loadRssiFile(const char* filename) {
    unsigned int t;
    unsigned int rssi;
    FILE* fp = fopen(filename, "r");
    for (adcDataCount = 0; adcDataCount < ADC_DATA_SIZE && fscanf(fp, "%u,%u\n", &t, &rssi) > 0; adcDataCount++) {
        adcDataTime[adcDataCount] = t;
        adcDataValues[adcDataCount] = rssi << 1; // scale-up to original adc value
    }
    fclose(fp);
    adcDataIndex = 0;
}

static volatile sig_atomic_t keepRunning = 1;

void onTerminate(int signum)
{
    keepRunning = 0;
}

int main(int argc, const char* argv[])
{
    signal(SIGINT, onTerminate);
    signal(SIGTERM, onTerminate);

    const char* addr = nullptr;
    const char* rssiFile = nullptr;
    int argIdx = 1;
    if (argIdx < argc) {
        if (strcmp(argv[argIdx], "REALTIME") == 0) {
            adcSignalClock = REALTIME;
            argIdx++;
        } else if (strcmp(argv[argIdx], "COUNTER") == 0) {
            adcSignalClock = COUNTER;
            argIdx++;
        }
    }
    if (argIdx < argc) {
        addr = argv[argIdx];
        argIdx++;
    }
    if (argIdx < argc) {
        rssiFile = argv[argIdx];
        argIdx++;
    }

    static timespec timerResolution;
    clock_getres(CLOCK_MONOTONIC, &timerResolution);
    fprintf(stderr, "Timer resolution %lds %ldns\n", timerResolution.tv_sec, timerResolution.tv_nsec);

    if (addr) {
#ifdef _WIN32
        initSerial(addr);
#else
        const char* sep = strchr(addr, ':');
        static char host[64];
        int len = sep-addr;
        if (len+1 > sizeof(host)) {
            fprintf(stderr, "Host name too long: %s\n", addr);
            return -1;
        }
        strncpy(host, addr, len);
        host[len] = '\0';
        int port = atoi(sep+1);
        initSocket(host, port);
#endif
    }
    if (rssiFile) {
        loadRssiFile(rssiFile);
    }

    startTime = millis();
    setup();

    unsigned long last_io = 0;
    while (keepRunning) {

        loop();

        unsigned long t = millis();
        if (t - last_io > 5) {
            perform_io();
            last_io = t;
        }
    }

    fprintf(stderr, "\nTerminating...\n");
#ifdef _WIN32
    closeSerial();
#else
    closeSocket();
#endif

    return 0;
}
