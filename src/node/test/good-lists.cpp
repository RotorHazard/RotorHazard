#include <ArduinoUnitTests.h>
#include "util/Lists.h"

unittest(arraylist)
{
  int a[] = {0, 1, 2};
  ArrayList<int,3> l(a);
  assertEqual(3, l.size());
  for(int i=0; i<l.size(); i++) {
      assertEqual(a[i], l[i]);
  }
}

unittest(slicedlist)
{
  int a[] = {0, 1, 2};
  ArrayList<int,3> l(a);
  SlicedList<int,3> sl(l, 1, 2);
  assertEqual(1, sl.size());
  assertEqual(a[1], sl[0]);
}

unittest_main()
