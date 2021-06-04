#include <ArduinoUnitTests.h>
#include "../io.h"

unittest(io8)
{
  Buffer<1,0> buf;
  uint8_t expected = 254;
  buf.write8(expected);
  assertEqual(1, buf.size);

  uint8_t result = buf.read8();
  assertEqual(1, buf.index);

  assertEqual(expected, result);
}

unittest(io16)
{
  Buffer<2,0> buf;
  uint16_t expected = 254*254;
  buf.write16(expected);
  assertEqual(2, buf.size);

  uint16_t result = buf.read16();
  assertEqual(2, buf.index);

  assertEqual(expected, result);
}

unittest(io32)
{
  Buffer<4,0> buf;
  uint32_t expected = 254*254*254*254;
  buf.write32(expected);
  assertEqual(4, buf.size);

  uint32_t result = buf.read32();
  assertEqual(4, buf.index);

  assertEqual(expected, result);
}

unittest(ioEmptyText)
{
  Buffer<5,4> buf;
  // add some garbage to the buffer
  buf.data[2] = 'X';
  buf.data[3] = 'Z';
  buf.writeText("");
  assertEqual(4, buf.size);
  for (int i=0; i<buf.textLength(); i++) {
      assertEqual('\0', buf.data[i]);
  }
}

unittest(ioText)
{
  Buffer<6,4> buf;
  buf.size = 1;
  buf.writeText("AB");
  assertEqual(5, buf.size);
  assertEqual('A', buf.data[0]);
  assertEqual('B', buf.data[1]);
  assertEqual('\0', buf.data[2]);
  assertEqual('\0', buf.data[3]);
}

unittest(ioTooLongText)
{
  Buffer<4,4> buf;
  buf.writeText("FOOBAR");
  assertEqual(4, buf.size);
  assertEqual('\0', buf.data[buf.textLength()-1]);
}

unittest(checksum)
{
  Buffer<3,2> buf;
  buf.write8(200);
  buf.write8(145);
  uint8_t checksum = buf.calculateChecksum(2);
  assertEqual(89, (int)checksum);
}

unittest_main()
