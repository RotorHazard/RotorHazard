#ifndef singlesendbuffer_h
#define singlesendbuffer_h

#include "rhtypes.h"
#include "sendbuffer.h"

#define endTime(x) ((x).firstTime + (x).duration)

class SinglePeakSendBuffer : public SendBuffer<Extremum>
{
    private:
        Extremum buffer = {0, 0, 0}; // only valid if buffer.rssi != 0
    public:
      bool isEmpty() {
          return !isPeakValid(buffer);
      }
      bool isFull() {
          return isPeakValid(buffer);
      }
      void addOrDiscard(const Extremum& e) {
          if(e.rssi > buffer.rssi) {
              // prefer higher peak
              buffer = e;
          } else if (e.rssi == buffer.rssi) {
              // merge
              buffer.duration = endTime(e) - buffer.firstTime;
          }
      }
      const Extremum first() {
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

class SingleNadirSendBuffer : public SendBuffer<Extremum>
{
    private:
        Extremum buffer = {MAX_RSSI, 0, 0}; // only valid if buffer.rssi != MAX_RSSI
    public:
      bool isEmpty() {
          return !isNadirValid(buffer);
      }
      bool isFull() {
          return isNadirValid(buffer);
      }
      void addOrDiscard(const Extremum& e) {
          if(e.rssi < buffer.rssi) {
              // prefer lower nadir
              buffer = e;
          } else if (e.rssi == buffer.rssi) {
              // merge
              buffer.duration = endTime(e) - buffer.firstTime;
          }
      }
      const Extremum first() {
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
