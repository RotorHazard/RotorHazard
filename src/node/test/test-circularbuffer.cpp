#include <ArduinoUnitTests.h>
#include "util/CircularBuffer.h"

unittest(copyTo)
{
    CircularBuffer<int,3> buf;
    CircularBuffer<int,3> expected;
    for (int t=1; t<=6; t++) {
        buf.push(t);
        expected.push(t);
        int out[] = {0, 0, 0};
        buf.copyTo(out);
        assertEqual(expected.size(), buf.size());
        for(int i=0; i<expected.size(); i++) {
          assertEqual(expected[i], out[i]);
        }
    }
}

unittest_main()
