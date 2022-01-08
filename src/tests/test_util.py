import unittest
from util import Averager
import numpy as np

class UtilTest(unittest.TestCase):
    def test_average(self):
        window_size = 10
        avg = Averager(window_size)
        samples = np.random.sample(10*window_size)
        for i, v in enumerate(samples):
            avg.append(v)
            offset = 1 if i >= window_size else 0
            last_window = samples[max(i-window_size,0)+offset:i+1]
            self.assert_stats(avg, last_window)

    def test_average_clear(self):
        window_size = 10
        avg = Averager(window_size)
        samples = np.random.sample(window_size)
        for v in samples:
            avg.append(v)
        self.assert_stats(avg, samples)
        avg.clear()
        self.assertIsNone(avg.min)
        self.assertIsNone(avg.max)
        self.assertIsNone(avg.mean)
        self.assertIsNone(avg.std)
        samples = np.random.sample(window_size)
        for v in samples:
            avg.append(v)
        self.assert_stats(avg, samples)

    def assert_stats(self, avg, expectedSamples):
        self.assertEqual(avg.min, np.min(expectedSamples))
        self.assertEqual(avg.max, np.max(expectedSamples))
        self.assertAlmostEqual(avg.mean, np.mean(expectedSamples), 10)
        self.assertAlmostEqual(avg.std, np.std(expectedSamples), 10)


if __name__ == '__main__':
    unittest.main()
