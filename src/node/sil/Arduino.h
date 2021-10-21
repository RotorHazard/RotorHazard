#ifndef arduino_h
#define arduino_h

#ifdef _WIN32
#include <winsock2.h>
#include <windows.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <errno.h>
#endif
#include <inttypes.h>
#include <string.h>

#include "WString.h"
#include "Stream.h"
#include "Client.h"
#include "../util/CircularBuffer.h"

#define HIGH 1
#define LOW  0

#define INPUT 0
#define OUTPUT 1

// pin definitions
#define LED_BUILTIN 1
#define MOSI 26
#define SCK  18

#define min(a,b) ((a)<(b)?(a):(b))
#define max(a,b) ((a)>(b)?(a):(b))
#define constrain(amt,low,high) ((amt)<(low)?(low):((amt)>(high)?(high):(amt)))

void pinMode(uint8_t pin, uint8_t mode);
void digitalWrite(uint8_t pin, uint8_t val);
int analogRead(uint8_t pin);
unsigned long millis();
unsigned long micros();
void delay(unsigned long ms);
void delayMicroseconds(unsigned int us);

class _BufferedStream {
private:
    CircularBuffer<uint8_t,128> buffer;
public:
    void _copyToBuffer(const uint8_t data[], size_t size);
    int read();
    int read(uint8_t* buf, size_t size);
    virtual size_t write(const uint8_t* buffer, size_t size) = 0;
    int available();
    virtual int _performIo() = 0;
    virtual void _close() = 0;
};

class _StreamWrapper : public Stream {
public:
    _BufferedStream* delegate;
    int available() override {
        return delegate->available();
    }
    int read() override {
        return delegate->read();
    }
    size_t write(const uint8_t* buf, size_t size) override {
        return delegate->write(buf, size);
    }
};

extern _StreamWrapper Serial;

#ifdef _WIN32
class HardwareSerial : public Stream, public _BufferedStream {
private:
    HANDLE hCom = 0;
public:
    void _open(const char* comPort);
    uint8_t connected();
    int available() override {
        return _BufferedStream::available();
    }
    int read() override {
        return _BufferedStream::read();
    }
    size_t write(const uint8_t* buf, size_t size);
    void end() { _close(); }
    int _performIo();
    void _close();
};
#endif

class WiFiClass {
public:
    void setHostname(const char* hostname);
    void enableSTA(bool flag);
    void setAutoReconnect(bool flag);
    void begin(const char* ssid, const char* password);
    void waitForConnectResult();
};

class WiFiClient : public Client, public _BufferedStream {
private:
#ifdef _WIN32
    SOCKET hSock = INVALID_SOCKET;
#else
    int sockfd = 0;
#endif
public:
    int _connectAttempts = 1;
    bool _serialEmulation = false;
    int connect(IPAddress ip, uint16_t port);
    int connect(const char* server, uint16_t port);
    uint8_t connected();
    int available() override {
        if (!_serialEmulation) {
            _performIo();
        }
        return _BufferedStream::available();
    }
    int read() override {
        if (!_serialEmulation) {
            _performIo();
        }
        return _BufferedStream::read();
    }
    int read(uint8_t* buf, size_t size) override {
        if (!_serialEmulation) {
            _performIo();
        }
        return _BufferedStream::read(buf, size);
    }
    size_t write(const uint8_t* buf, size_t size) override;
    void stop() { _close(); }
    int _performIo();
    void _close();
};

extern WiFiClass WiFi;

#endif
