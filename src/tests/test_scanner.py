import unittest
import gevent
from rh.tools import scanner

class ScannerTest(unittest.TestCase):
    class DummySocket():
        def emit(self, cmd, data):
            self.last_data = data

    def test(self):
        socket_io = ScannerTest.DummySocket()
        scanner.scan('MOCK', socket_io)
        gevent.sleep(0.3)
        self.assertIn('frequency', socket_io.last_data)
        self.assertTrue(len(socket_io.last_data['frequency']) > 0)


if __name__ == '__main__':
    unittest.main()
