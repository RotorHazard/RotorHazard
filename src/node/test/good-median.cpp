#include <ArduinoUnitTests.h>
#include "../FastRunningMedian.h"

unittest(median)
{
  FastRunningMedian<uint16_t, 5, 0> median;
  median.init();
  assertFalse(median.isFilled());
  while(!median.isFilled()) {
      median.addValue(1);
  }
  assertEqual(1, median.getMedian());
  median.addValue(1);
  assertEqual(1, median.getMedian());
  median.addValue(4);
  assertEqual(1, median.getMedian());
  median.addValue(3);
  assertEqual(1, median.getMedian());
  median.addValue(7);
  assertEqual(3, median.getMedian());
  median.addValue(5);
  assertEqual(4, median.getMedian());
  median.addValue(2);
  assertEqual(4, median.getMedian());
}

unittest_main()
