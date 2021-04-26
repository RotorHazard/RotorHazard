#include <ArduinoUnitTests.h>
#include "../io.h"

unittest(io8)
{
  Buffer<1> buf;
  uint8_t expected = 254;
  buf.write8(expected);
  assertEqual(1, buf.size);

  uint8_t result = buf.read8();
  assertEqual(1, buf.index);

  assertEqual(expected, result);
}

unittest(io16)
{
  Buffer<2> buf;
  uint16_t expected = 254*254;
  buf.write16(expected);
  assertEqual(2, buf.size);

  uint16_t result = buf.read16();
  assertEqual(2, buf.index);

  assertEqual(expected, result);
}

unittest(io32)
{
  Buffer<4> buf;
  uint32_t expected = 254*254*254*254;
  buf.write32(expected);
  assertEqual(4, buf.size);

  uint32_t result = buf.read32();
  assertEqual(4, buf.index);

  assertEqual(expected, result);
}

unittest_main()
