#include "filter.h"
#include "cyclicbuffer.h"
#include "FastRunningMedian.h"

template <typename T, uint8_t N, T default_value> class MedianFilter : public Filter<T> {

public:
  bool isFilled() {
    return median.isFilled();
  }

  void addRawValue(mtime_t ts, T value) {
    median.addValue(value);
    timestamps.addLast(ts);
  }

  T getFilteredValue() {
    return median.getMedian();
  }

  mtime_t getFilterTimestamp() {
    return timestamps.getFirst();
  }

  uint8_t getSampleCapacity() {
    return N;
  }

  uint8_t getTimestampCapacity() {
    return timestamps.getCapacity();
  }

private:
  FastRunningMedian<T,N,default_value> median;
  CyclicBuffer<mtime_t,(N+1)/2> timestamps; // size is half median window, rounded up
};

#define SmoothingSamples 255

MedianFilter<rssi_t, SmoothingSamples, 0> _filter;
