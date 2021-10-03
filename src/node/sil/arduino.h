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

class Stream {
private:
    CircularBuffer<uint8_t,128> buffer;
public:
    void copyToBuffer(const uint8_t data[], size_t size);
    int read();
    size_t write(const uint8_t* buffer, size_t size);
};

extern Stream Serial;
