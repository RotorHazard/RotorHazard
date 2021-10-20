#ifndef stream_h
#define stream_h

class Stream {
public:
    virtual int available() = 0;
    virtual int read() = 0;
    virtual size_t write(const uint8_t* buffer, size_t size) = 0;
};

#endif
