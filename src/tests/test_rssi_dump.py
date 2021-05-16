import unittest
import gevent
from tools import rssi_dump

class RssiDumpTest(unittest.TestCase):
    def test(self):
        buffers = {}
        def write_buffer(filename, buf):
            nonlocal buffers
            buffers[filename] = buf

        thread = gevent.spawn(rssi_dump.start, 'MOCK', 5885, write_buffer)
        gevent.sleep(0.3)
        thread.kill()
        self.assertGreater(len(buffers), 0)
        self.assertGreaterEqual(len(next(iter(buffers.values()))), 16, buffers)

if __name__ == '__main__':
    unittest.main()
