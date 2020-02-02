#include "filter.h"
#include "FastRunningMedian.h"
#define CIRCULAR_BUFFER_INT_SAFE
#include "CircularBuffer.h"

template <typename T, uint8_t N, T default_value> class MedianFilter : public Filter<T>
{
    private:
      FastRunningMedian<T,N,default_value> median;
      CircularBuffer<mtime_t,(N+1)/2> timestamps; // size is half median window, rounded up
    public:
      bool isFilled() {
        return median.isFilled();
      }

      void addRawValue(mtime_t ts, T value) {
        median.addValue(value);
        timestamps.push(ts);
      }

      T getFilteredValue() {
        return median.getMedian();
      }

      mtime_t getFilterTimestamp() {
        return timestamps.first();
      }

      uint8_t getSampleCapacity() {
        return N;
      }

      uint8_t getTimestampCapacity() {
        return timestamps.capacity;
      }
};

#define SmoothingSamples 255
