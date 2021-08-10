import unittest
from interface import calculate_checksum

class InterfaceTest(unittest.TestCase):
    def test_checksum(self):
        data = bytearray([200, 145])
        checksum = calculate_checksum(data)
        self.assertEqual(89, checksum)


if __name__ == '__main__':
    unittest.main()
