#ifndef multisendbuffer_h
#define multisendbuffer_h

#include "rhtypes.h"
#include "sendbuffer.h"
#include "CircularBuffer.h"

template <uint8_t N> class MultiExtremumSendBuffer : public ExtremumSendBuffer
{
    private:
      CircularBuffer<Extremum,N> buffer;
    public:
      uint_fast8_t size() const {
          return buffer.size();
      }
      bool isEmpty() const {
          return buffer.isEmpty();
      }
      bool isFull() const {
          return buffer.isFull();
      }
      void addOrDiscard(const Extremum& e, bool wasLast) {
          add(e);
      }
      const Extremum first() {
          return buffer.first();
      }
      const Extremum last() {
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
      void removeLast() {
          buffer.pop();
      }
};

template <uint8_t N> class MultiPeakSendBuffer : public MultiExtremumSendBuffer<N>
{
    public:
        void addOrDiscard(const Extremum& e, bool wasLast = true) {
            if (MultiExtremumSendBuffer<N>::isFull()) {
                Extremum last = MultiExtremumSendBuffer<N>::last();
                if (e.rssi > last.rssi) {
                    // prefer higher peak
                    MultiExtremumSendBuffer<N>::removeLast();
                    MultiExtremumSendBuffer<N>::add(e);
                } else if (wasLast && e.rssi == last.rssi) {
                    // merge
                    Extremum merged = {last.rssi, last.firstTime, (uint16_t) (endTime(e) - last.firstTime)};
                    MultiExtremumSendBuffer<N>::removeLast();
                    MultiExtremumSendBuffer<N>::add(merged);
                }
            } else {
                MultiExtremumSendBuffer<N>::add(e);
            }
        }
};

template <uint8_t N> class MultiNadirSendBuffer : public MultiExtremumSendBuffer<N>
{
    public:
        void addOrDiscard(const Extremum& e, bool wasLast = true) {
            if (MultiExtremumSendBuffer<N>::isFull()) {
                Extremum last = MultiExtremumSendBuffer<N>::last();
                if (e.rssi < last.rssi) {
                    // prefer lower peak
                    MultiExtremumSendBuffer<N>::removeLast();
                    MultiExtremumSendBuffer<N>::add(e);
                } else if (wasLast && e.rssi == last.rssi) {
                    // merge
                    Extremum merged = {last.rssi, last.firstTime, (uint16_t) (endTime(e) - last.firstTime)};
                    MultiExtremumSendBuffer<N>::removeLast();
                    MultiExtremumSendBuffer<N>::add(merged);
                }
            } else {
                MultiExtremumSendBuffer<N>::add(e);
            }
        }
};

#endif
