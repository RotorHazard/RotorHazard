#ifndef client_h
#define client_h

#include "Stream.h"
#include "IPAddress.h"

class Client : public Stream {
public:
    virtual int connect(IPAddress ip, uint16_t port) = 0;
    virtual int connect(const char* host, uint16_t port) = 0;
    virtual uint8_t connected() = 0;
    virtual int read(uint8_t* buf, size_t size) = 0;
    virtual void stop() = 0;
};

#endif
