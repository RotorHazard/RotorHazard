#ifndef multisendbuffer_h
#define multisendbuffer_h

#include "rhtypes.h"
#include "sendbuffer.h"
#define CIRCULAR_BUFFER_INT_SAFE
#include "CircularBuffer.h"

template <typename T, uint8_t N> class MultiSendBuffer : public SendBuffer<T>
{
    protected:
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

template <uint8_t N> class MultiPeakSendBuffer : public MultiSendBuffer<Extremum,N>
{
    public:
        void addOrDiscard(const Extremum& e) {
            if (MultiSendBuffer<Extremum,N>::isFull()) {
                Extremum last = MultiSendBuffer<Extremum,N>::buffer.last();
                if (e.rssi > last.rssi) {
                    MultiSendBuffer<Extremum,N>::buffer.push(e);
                } else if (e.rssi == last.rssi) {
                    // merge
                    Extremum merged = {last.rssi, last.firstTime, endTime(e) - last.firstTime};
                    MultiSendBuffer<Extremum,N>::buffer.push(merged);
                }
            } else {
                MultiSendBuffer<Extremum,N>::buffer.push(e);
            }
        }
};

template <uint8_t N> class MultiNadirSendBuffer : public MultiSendBuffer<Extremum,N>
{
    public:
        void addOrDiscard(const Extremum& e) {
            if (MultiSendBuffer<Extremum,N>::isFull()) {
                Extremum last = MultiSendBuffer<Extremum,N>::buffer.last();
                if (e.rssi < last.rssi) {
                    MultiSendBuffer<Extremum,N>::buffer.push(e);
                } else if (e.rssi == last.rssi) {
                    // merge
                    Extremum merged = {last.rssi, last.firstTime, endTime(e) - last.firstTime};
                    MultiSendBuffer<Extremum,N>::buffer.push(merged);
                }
            } else {
                MultiSendBuffer<Extremum,N>::buffer.push(e);
            }
        }
};

#endif
