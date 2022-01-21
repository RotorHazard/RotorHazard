#ifndef singlesendbuffer_h
#define singlesendbuffer_h

#include "rhtypes.h"
#include "sendbuffer.h"

class SinglePeakSendBuffer : public ExtremumSendBuffer
{
    private:
        Extremum buffer = {0, 0, 0}; // only valid if buffer.rssi != 0
    public:
      uint_fast8_t size() const {
          return isFull() ? 1 : 0;
      }
      bool isEmpty() const {
          return !isPeakValid(buffer);
      }
      bool isFull() const {
          return isPeakValid(buffer);
      }
      void addOrDiscard(const Extremum& e, bool wasLast = true) {
          if(e.rssi > buffer.rssi) {
              // prefer higher peak
              buffer = e;
          } else if (wasLast && e.rssi == buffer.rssi) {
              // merge
              buffer.duration = endTime(e) - buffer.firstTime;
          }
      }
      const Extremum first() const {
          return buffer;
      }
      const Extremum last() const {
          return buffer;
      }
      void removeFirst() {
          invalidatePeak(buffer);
      }
      void clear() {
          invalidatePeak(buffer);
      }
    protected:
      void add(const Extremum& e) {
          buffer = e;
      }
};

class SingleNadirSendBuffer : public ExtremumSendBuffer
{
    private:
        Extremum buffer = {MAX_RSSI, 0, 0}; // only valid if buffer.rssi != MAX_RSSI
    public:
      uint_fast8_t size() const {
          return isFull() ? 1 : 0;
      }
      bool isEmpty() const {
          return !isNadirValid(buffer);
      }
      bool isFull() const {
          return isNadirValid(buffer);
      }
      void addOrDiscard(const Extremum& e, bool wasLast = true) {
          if(e.rssi < buffer.rssi) {
              // prefer lower nadir
              buffer = e;
          } else if (wasLast && e.rssi == buffer.rssi) {
              // merge
              buffer.duration = endTime(e) - buffer.firstTime;
          }
      }
      const Extremum first() const {
          return buffer;
      }
      const Extremum last() const {
          return buffer;
      }
      void removeFirst() {
          invalidateNadir(buffer);
      }
      void clear() {
          invalidateNadir(buffer);
      }
    protected:
      void add(const Extremum& e) {
          buffer = e;
      }
};

#endif
