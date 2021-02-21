#ifdef _WIN32
#include <windows.h>
#endif
#include <inttypes.h>
#include "../util/CircularBuffer.h"

#define HIGH 1
#define LOW  0

#define INPUT 0
#define OUTPUT 1

#define LED_BUILTIN 0

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
    void bufferRead(const uint8_t data[], size_t size);
    int read();
    size_t write(const uint8_t *buffer, size_t size);
};

extern Stream Serial;
