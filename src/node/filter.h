#ifndef filter_h
#define filter_h

#include "rhtypes.h"

template <typename T> class Filter {

public:
  /**
   * Returns true if the filter has sufficient samples.
   */
  virtual bool isFilled() = 0;
  virtual void addRawValue(mtime_t ts, T value) = 0;
  virtual T getFilteredValue() = 0;
  virtual mtime_t getFilterTimestamp() = 0;
};

#endif
