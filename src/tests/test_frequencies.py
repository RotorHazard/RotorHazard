'''python -m unittest discover'''
import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'server'))

import frequencies

class FrequenciesTest(unittest.TestCase):
    def test_band_channel_for(self):
        self.assertEqual(frequencies.band_channel_for(5658), ('R', 1))
        self.assertEqual(frequencies.band_channel_for(5866), ('B', 8))
        # frequencies shared by several bands take the first in table order
        self.assertEqual(frequencies.band_channel_for(5695), ('R', 2))
        self.assertEqual(frequencies.band_channel_for(5880), ('R', 7))
        self.assertEqual(frequencies.band_channel_for(5300), ('U', 0))
        self.assertEqual(frequencies.band_channel_for(5555), (None, None))
        self.assertEqual(frequencies.band_channel_for(0), (None, None))
        self.assertEqual(frequencies.band_channel_for(None), (None, None))

    def test_frequency_for(self):
        self.assertEqual(frequencies.frequency_for('R', 1), 5658)
        self.assertEqual(frequencies.frequency_for('U', 0), 5300)
        self.assertIsNone(frequencies.frequency_for('R', 9))
        self.assertIsNone(frequencies.frequency_for(None, 1))
        self.assertIsNone(frequencies.frequency_for('R', None))

    def test_fill_missing_band_channels(self):
        freqs = {'b': [None, 'B', None, 0, 'U', None],
                 'c': [None, 8, None, 0, 0, None],
                 'f': [5658, 5866, 0, 5800, 5300, 5555]}
        self.assertEqual(frequencies.fill_missing_band_channels(freqs), [0, 3])
        self.assertEqual(freqs['b'], ['R', 'B', None, 'F', 'U', None])
        self.assertEqual(freqs['c'], [1, 8, None, 4, 0, None])
        self.assertEqual(freqs['f'], [5658, 5866, 0, 5800, 5300, 5555])
        # nothing left to fill on a second pass
        self.assertEqual(frequencies.fill_missing_band_channels(freqs), [])

    def test_fill_missing_band_channels_short_lists(self):
        freqs = {'f': [5732, 0]}
        self.assertEqual(frequencies.fill_missing_band_channels(freqs), [0])
        self.assertEqual(freqs['b'], ['R', None])
        self.assertEqual(freqs['c'], [3, None])

if __name__ == '__main__':
    unittest.main()
