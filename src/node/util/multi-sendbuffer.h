#ifndef multisendbuffer_h
#define multisendbuffer_h

#include "rhtypes.h"
#include "sendbuffer.h"
#include "CircularBuffer.h"

template <uint8_t N> class MultiExtremumSendBuffer : public ExtremumSendBuffer
{
    protected:
        CircularBuffer<Extremum,N> buffer;
    public:
      bool isEmpty() {
          return buffer.isEmpty();
      }
      bool isFull() {
          return buffer.isFull();
      }
      void addOrDiscard(const Extremum& e) {
          buffer.push(e);
      }
      const Extremum first() {
          return buffer.first();
      }
      void removeFirst() {
          buffer.shift();
      }
      void clear() {
          buffer.clear();
      }
    protected:
      void add(const Extremum& e) {
          buffer.push(e);
      }
};

template <uint8_t N> class MultiPeakSendBuffer : public MultiExtremumSendBuffer<N>
{
    public:
        void addOrDiscard(const Extremum& e) {
            if (MultiExtremumSendBuffer<N>::isFull()) {
                Extremum last = MultiExtremumSendBuffer<N>::buffer.last();
                if (e.rssi > last.rssi) {
                    MultiExtremumSendBuffer<N>::buffer.push(e);
                } else if (e.rssi == last.rssi) {
                    // merge
                    Extremum merged = {last.rssi, last.firstTime, (uint16_t) (endTime(e) - last.firstTime)};
                    MultiExtremumSendBuffer<N>::buffer.push(merged);
                }
            } else {
                MultiExtremumSendBuffer<N>::buffer.push(e);
            }
        }
};

template <uint8_t N> class MultiNadirSendBuffer : public MultiExtremumSendBuffer<N>
{
    public:
        void addOrDiscard(const Extremum& e) {
            if (MultiExtremumSendBuffer<N>::isFull()) {
                Extremum last = MultiExtremumSendBuffer<N>::buffer.last();
                if (e.rssi < last.rssi) {
                    MultiExtremumSendBuffer<N>::buffer.push(e);
                } else if (e.rssi == last.rssi) {
                    // merge
                    Extremum merged = {last.rssi, last.firstTime, (uint16_t) (endTime(e) - last.firstTime)};
                    MultiExtremumSendBuffer<N>::buffer.push(merged);
                }
            } else {
                MultiExtremumSendBuffer<N>::buffer.push(e);
            }
        }
};

#endif
