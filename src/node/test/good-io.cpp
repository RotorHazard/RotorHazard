#include <ArduinoUnitTests.h>
#include "../io.h"

unittest(io8)
{
  Buffer_t buf;
  uint8_t expected = 254;
  ioBufferWrite8(&buf, expected);
  assertEqual(1, buf.size);

  uint8_t result = ioBufferRead8(&buf);
  assertEqual(1, buf.index);

  assertEqual(expected, result);
}

unittest(io16)
{
  Buffer_t buf;
  uint16_t expected = 254*254;
  ioBufferWrite16(&buf, expected);
  assertEqual(2, buf.size);

  uint16_t result = ioBufferRead16(&buf);
  assertEqual(2, buf.index);

  assertEqual(expected, result);
}

unittest(io32)
{
  Buffer_t buf;
  uint32_t expected = 254*254*254*254;
  ioBufferWrite32(&buf, expected);
  assertEqual(4, buf.size);

  uint32_t result = ioBufferRead32(&buf);
  assertEqual(4, buf.index);

  assertEqual(expected, result);
}

unittest_main()
