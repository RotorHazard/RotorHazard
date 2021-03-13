#ifndef filter_h
#define filter_h

#include "rhtypes.h"

template <typename T> class Filter {
public:
    Filter() = default;
    Filter(const Filter&) = delete;
    Filter(Filter&&) = delete;
    Filter& operator=(const Filter&) = delete;
    Filter& operator=(Filter&&) = delete;
  /**
   * Returns true if the filter has sufficient samples.
   */
  virtual bool isFilled() const = 0;
  virtual void addRawValue(mtime_t ts, T value) = 0;
  virtual T getFilteredValue() const = 0;
  virtual mtime_t getFilterTimestamp() const = 0;
  virtual void reset() = 0;
};

#endif
