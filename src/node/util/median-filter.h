#ifndef MEDIAN_FILTER_H
#define MEDIAN_FILTER_H

#include "filter.h"
#include "FastRunningMedian.h"
#include "CircularBuffer.h"

//non-linear!!!
template <typename T, uint8_t N, T default_value> class MedianFilter final : public Filter<T>
{
    private:
      FastRunningMedian<T,N,default_value> median;
      CircularBuffer<mtime_t,(N+1)/2> timestamps; // size is half median window, rounded up
    public:
      bool isFilled() const {
        return median.isFilled();
      }

      void addRawValue(mtime_t ts, T value) {
        median.addValue(value);
        timestamps.push(ts);
      }

      T getFilteredValue() const {
        return median.getMedian();
      }

      mtime_t getFilterTimestamp() const {
        return timestamps.first();
      }

      constexpr uint8_t getSampleCapacity() {
        return N;
      }

      constexpr uint8_t getTimestampCapacity() const {
        return timestamps.capacity;
      }

      void reset() {
          median.reset();
          timestamps.clear();
      }
};

#define SmoothingSamples 255

#endif  //MEDIAN_FILTER_H
