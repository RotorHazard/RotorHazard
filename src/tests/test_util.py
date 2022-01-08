import unittest
from util import Averager
import numpy as np

class UtilTest(unittest.TestCase):
    def test_average(self):
        window_size = 10
        for n in range(1,2*window_size):
            samples = np.random.sample(n)
            avg = Averager(window_size)
            for v in samples:
                avg.append(v)
            last_window = samples[-window_size:]
            self.assertEqual(avg.min, np.min(last_window))
            self.assertEqual(avg.max, np.max(last_window))
            self.assertAlmostEqual(avg.mean, np.mean(last_window), 10)
            self.assertAlmostEqual(avg.std, np.std(last_window), 10)


if __name__ == '__main__':
    unittest.main()
