#include "Arduino.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <signal.h>

constexpr size_t ADC_DATA_SIZE = 1000;

void pinMode(uint8_t pin, uint8_t mode) {

}

constexpr size_t PINOUT_BUFFER_SIZE = 4096;

static FILE* pinOutFile = nullptr;
static int pinOutBufferIndex = 0;
static uint32_t pinOutTimeBuffer[PINOUT_BUFFER_SIZE];
static uint8_t pinOutPinBuffer[PINOUT_BUFFER_SIZE], pinOutValueBuffer[PINOUT_BUFFER_SIZE];

static void flushPinOutBuffers() {
    for (int i=0; i<pinOutBufferIndex; i++) {
        fprintf(pinOutFile, "%u, %u, %u\n", pinOutTimeBuffer[i], pinOutPinBuffer[i], pinOutValueBuffer[i]);
    }
    pinOutBufferIndex = 0;
}

void digitalWrite(uint8_t pin, uint8_t val) {
    if (pinOutFile) {
        pinOutTimeBuffer[pinOutBufferIndex] = micros();
        pinOutPinBuffer[pinOutBufferIndex] = pin;
        pinOutValueBuffer[pinOutBufferIndex] = val;
        pinOutBufferIndex++;
        if (pinOutBufferIndex == PINOUT_BUFFER_SIZE) {
            flushPinOutBuffers();
        }
    }
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

_StreamWrapper Serial;

int _BufferedStream::read() {
    return buffer.shift();
}

int _BufferedStream::read(uint8_t* buf, size_t size) {
    int i=0;
    for (; i<size && i<buffer.size(); i++) {
        buf[i] = read();
    }
    return i;
}

int _BufferedStream::available() {
    return buffer.size();
}

void _BufferedStream::_copyToBuffer(const uint8_t data[], size_t size) {
    if (size > buffer.available()) {
        fprintf(stderr, "Stream read buffer overflow\n");
    }
    for(int i=0; i<size; i++) {
        buffer.push(data[i]);
    }
}

#ifdef _WIN32
void HardwareSerial::_open(const char* comPort) {
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
        end();
        return;
    }
    dcb.BaudRate = CBR_115200;
    dcb.ByteSize = 8;
    dcb.Parity = NOPARITY;
    dcb.StopBits = ONESTOPBIT;
    if (!SetCommState(hCom, &dcb)) {
        fprintf(stderr, "Error setting comm state: %d\n", GetLastError());
        end();
        return;
    }
    COMMTIMEOUTS ctos = {MAXDWORD, 0, 0, 0, 1};
    if (!SetCommTimeouts(hCom, &ctos)) {
        fprintf(stderr, "Error setting comm timeouts: %d\n", GetLastError());
        end();
        return;
    }

    fprintf(stderr, "Opened serial port %s\n", comPort);
}

uint8_t HardwareSerial::connected() {
    return hCom > 0;
}

void HardwareSerial::_close() {
    if (hCom > 0) {
        CloseHandle(hCom);
        hCom = 0;
    }
}

size_t HardwareSerial::write(const uint8_t* buffer, size_t size) {
    if (connected()) {
        DWORD dwBytesWritten;
        if (WriteFile(hCom, buffer, size, &dwBytesWritten, NULL)) {
            return dwBytesWritten;
        } else {
            fprintf(stderr, "Serial write failed\n");
        }
    }
    return 0;
}

int HardwareSerial::_performIo() {
    int bytesRead = -1;
    if (connected()) {
        uint8_t buffer[128];
        DWORD dwBytesRead;
        if (ReadFile(hCom, buffer, sizeof(buffer), &dwBytesRead, NULL)) {
            if (dwBytesRead == sizeof(buffer)) {
                fprintf(stderr, "Serial read buffer overflow\n");
            }
            _copyToBuffer(buffer, dwBytesRead);
            bytesRead = dwBytesRead;
        } else {
            fprintf(stderr, "Serial read failed\n");
            end();
        }
    }
    return bytesRead;
}


int WiFiClient::connect(const char* host, uint16_t port) {
    struct addrinfo hints, *result = nullptr;
    SecureZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;
    char szPort[6];
    itoa(port, szPort, 10);
    int rc = getaddrinfo(host, szPort, &hints, &result);
    if (rc != 0) {
        fprintf(stderr, "Unknown host %s: %d\n", host, rc);
        stop();
        return 0;
    }

    hSock = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (hSock == INVALID_SOCKET) {
        fprintf(stderr, "Failed to create socket: %d\n", WSAGetLastError());
        stop();
        return 0;
    }

    rc = SOCKET_ERROR;
    for (int i=0; i<_connectAttempts; i++) {
        rc = ::connect(hSock, result->ai_addr, (int)result->ai_addrlen);
        if (rc != SOCKET_ERROR) {
            break;
        }
        Sleep(1000);
    }
    freeaddrinfo(result);
    if (rc == SOCKET_ERROR) {
        fprintf(stderr, "Failed to connect to %s:%d\n", host, port);
        stop();
        return 0;
    }

    fprintf(stderr, "Connected to %s:%d\n", host, port);
    return 1;
}

uint8_t WiFiClient::connected() {
    return hSock != INVALID_SOCKET;
}

void WiFiClient::_close() {
    if (hSock != INVALID_SOCKET) {
        closesocket(hSock);
        hSock = INVALID_SOCKET;
    }
}

size_t WiFiClient::write(const uint8_t* buffer, size_t size) {
    if (connected()) {
        int bytesWritten = send(hSock, (char*)buffer, size, 0);
        if (bytesWritten != SOCKET_ERROR) {
            return bytesWritten;
        } else {
            fprintf(stderr, "Socket write failed: %d\n", WSAGetLastError());
        }
    }
    return 0;
}

int WiFiClient::_performIo() {
    int bytesRead = -1;
    if (connected()) {
        u_long nbioFlag = 1;
        if (ioctlsocket(hSock, FIONBIO, &nbioFlag)) {
            fprintf(stderr, "WARNING: Could not set non-blocking mode.\n");
        }

        uint8_t buffer[128];
        bytesRead = recv(hSock, (char*)buffer, sizeof(buffer), 0);
        if (bytesRead > 0) {
            if (bytesRead == sizeof(buffer)) {
                fprintf(stderr, "Socket read buffer overflow\n");
            }
            _copyToBuffer(buffer, bytesRead);
        } else if (bytesRead == 0) {
            fprintf(stderr, "Socket connection closed\n");
            stop();
        } else {
            const int err = WSAGetLastError();
            if (err == WSAEWOULDBLOCK) {
                bytesRead = 0;
            } else {
                fprintf(stderr, "Socket read failed: %d\n", err);
                stop();
            }
        }

        if (connected()) {
            nbioFlag = 0;
            ioctlsocket(hSock, FIONBIO, &nbioFlag);
        }
    }
    return bytesRead;
}
#else

int WiFiClient::connect(const char* host, uint16_t port) {
    struct hostent* hostinfo = gethostbyname(host);
    if (hostinfo == nullptr) {
        fprintf(stderr, "Unknown host %s\n", host);
        return 0;
    }

    sockaddr_in sock_addr;
    sock_addr.sin_family = AF_INET;
    sock_addr.sin_port = htons(port);
    sock_addr.sin_addr.s_addr = *(uint32_t*) (hostinfo->h_addr);

    sockfd = socket(PF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        fprintf(stderr, "Failed to create socket\n");
        return 0;
    }

    bool connected = false;
    for (int i=0; i<_connectAttempts; i++) {
        connected = (::connect(sockfd, (struct sockaddr *) &sock_addr, sizeof(sock_addr)) == 0);
        if (connected) {
            break;
        }
        sleep(1);
    }
    if (!connected) {
        fprintf(stderr, "Failed to connect to %s:%d\n", host, port);
        stop();
        return 0;
    }

    fprintf(stderr, "Connected to %s:%d\n", host, port);
    return 1;
}

void WiFiClient::_close() {
    if (sockfd > 0) {
        close(sockfd);
        sockfd = 0;
    }
}

uint8_t WiFiClient::connected() {
    return sockfd > 0;
}

size_t WiFiClient::write(const uint8_t* buffer, size_t size) {
    if (connected()) {
        ssize_t bytesWritten = ::write(sockfd, buffer, size);
        if (bytesWritten >= 0) {
            return bytesWritten;
        } else {
            fprintf(stderr, "Socket write failed: %d\n", errno);
            stop();
        }
    }
    return 0;
}

int WiFiClient::_performIo() {
    ssize_t bytesRead = -1;
    if (connected()) {
        uint8_t buffer[128];
        bytesRead = recv(sockfd, buffer, sizeof(buffer), MSG_DONTWAIT);
        if (bytesRead > 0) {
            if (bytesRead == sizeof(buffer)) {
                fprintf(stderr, "Socket read buffer overflow\n");
            }
            _copyToBuffer(buffer, bytesRead);
        } else if (bytesRead == 0) {
            fprintf(stderr, "Socket connection closed\n");
            stop();
        } else if (errno != EAGAIN && errno != EWOULDBLOCK) {
            fprintf(stderr, "Socket read failed: %d\n", errno);
            stop();
        }
    }
    return bytesRead;
}
#endif

int WiFiClient::connect(IPAddress ip, uint16_t port) {
    return 0;
}

void WiFiClass::setHostname(const char* hostname) {

}

void WiFiClass::enableSTA(bool flag) {

}

void WiFiClass::setAutoReconnect(bool flag) {

}

void WiFiClass::begin(const char* ssid, const char* password) {

}

void WiFiClass::waitForConnectResult() {

}

WiFiClass WiFi;



static void loadRssiFile(const char* filename) {
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

static void openPinOutFile(const char* filename) {
    pinOutFile = fopen(filename, "w");
    fprintf(pinOutFile, "time, pin, value\n");
}

static void closePinOutFile() {
    if (pinOutFile) {
        flushPinOutBuffers();
        fclose(pinOutFile);
    }
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
    const char* rssiFileName = nullptr;
    const char* pinOutFileName = nullptr;
    int argIdx = 1;
    if (argIdx < argc) {
        if (strcmp(argv[argIdx], "adcClock=REALTIME") == 0) {
            adcSignalClock = REALTIME;
            argIdx++;
        } else if (strcmp(argv[argIdx], "adcClock=COUNTER") == 0) {
            adcSignalClock = COUNTER;
            argIdx++;
        }
    }
    if (argIdx < argc) {
        const char* const option = "rssi=";
        int n = strlen(option);
        if (strncmp(argv[argIdx], option, n) == 0) {
            rssiFileName = argv[argIdx] + n;
            argIdx++;
        }
    }
    if (argIdx < argc) {
        const char* const option = "pinOut=";
        int n = strlen(option);
        if (strncmp(argv[argIdx], option, n) == 0) {
            pinOutFileName = argv[argIdx] + n;
            argIdx++;
        }
    }
    if (argIdx < argc) {
        addr = argv[argIdx];
        argIdx++;
    }

    static timespec timerResolution;
    clock_getres(CLOCK_MONOTONIC, &timerResolution);
    fprintf(stderr, "Timer resolution %lds %ldns\n", timerResolution.tv_sec, timerResolution.tv_nsec);

#ifdef _WIN32
    WSADATA wsaData;
    int rc = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (rc != 0) {
        fprintf(stderr, "WSAStartup failed: %d\n", rc);
        return -1;
    }
#endif

    if (addr) {
        const char* sep = strchr(addr, ':');
        if (sep) {
            static char host[64];
            int len = sep-addr;
            if (len+1 > sizeof(host)) {
                fprintf(stderr, "Host name too long: %s\n", addr);
                return -1;
            }
            strncpy(host, addr, len);
            host[len] = '\0';
            int port = atoi(sep+1);
            WiFiClient* netClient = new WiFiClient();
            netClient->_connectAttempts = 30;
            netClient->_serialEmulation = true;
            netClient->connect(host, port);
            Serial.delegate = netClient;
        } else {
#ifdef _WIN32
            HardwareSerial* serial = new HardwareSerial();
            serial->_open(addr);
            Serial.delegate = serial;
#else
            fprintf(stderr, "Serial ports not supported\n");
#endif
        }
    } else {
        fprintf(stderr, "No comm link specified - won't attempt connection\n");
    }

    if (rssiFileName) {
        loadRssiFile(rssiFileName);
    }
    if (pinOutFileName) {
        openPinOutFile(pinOutFileName);
    }

    startTime = millis();
    setup();

    unsigned long last_io = 0;
    while (keepRunning) {

        loop();

        unsigned long t = millis();
        if (t - last_io > 5) {
            int bytesRead = Serial.delegate->_performIo();
            if (bytesRead > 0) {
                for (int i=0; i<bytesRead; i++) {
                    serialEvent();
                }
            }
            last_io = t;
        }
    }

    fprintf(stderr, "\nTerminating...\n");

    Serial.delegate->_close();
    closePinOutFile();

#ifdef _WIN32
    WSACleanup();
#endif

    return 0;
}
