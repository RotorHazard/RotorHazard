#ifndef multisendbuffer_h
#define multisendbuffer_h

#include "rhtypes.h"
#include "sendbuffer.h"
#define CIRCULAR_BUFFER_INT_SAFE
#include "CircularBuffer.h"

template <typename T, uint8_t N> class MultiSendBuffer : public SendBuffer<T>
{
    private:
        CircularBuffer<T,N> buffer;
    public:
      bool isEmpty() {
          return buffer.isEmpty();
      }
      bool isFull() {
          return buffer.isFull();
      }
      void addOrDiscard(const T& e) {
          buffer.push(e);
      }
      const T first() {
          return buffer.first();
      }
      void removeFirst() {
          buffer.shift();
      }
      void clear() {
          buffer.clear();
      }
    protected:
      void add(const T& e) {
          buffer.push(e);
      }
};

#endif
