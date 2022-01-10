import rh.util.persistent_homology as ph
import unittest
import numpy as np

class PersistentHomologyTest(unittest.TestCase):
    def test_PeakPersistentHomology(self):
        data = [30, 29, 41, 4, 114, 1, 3, 2, 33, 9, 112, 40, 118]
        ccs = ph.calculatePeakPersistentHomology(data)
        ccs = ph.sortByLifetime(ccs)
        self.assertEqual(str(ccs), '[(12, 118) -> (5, 1), (4, 114) -> (5, 1), (10, 112) -> (11, 40), (2, 41) -> (3, 4), (8, 33) -> (9, 9), (0, 30) -> (1, 29), (6, 3) -> (7, 2)]')

    def test_findBreak_1(self):
        data = [2,0,5,0,2,0,8,2,4,0,6,0,9,0,15,6,10,8]
        ccs = ph.calculatePeakPersistentHomology(data)
        actual_levels = np.unique([cc.lifetime() for cc in ccs]).tolist()
        expected_levels = [2, 4, 5, 6, 8, 9, 15]
        self.assertListEqual(actual_levels, expected_levels)
        bounds = ph.findBreak(ccs)
        self.assertEqual(bounds, (6, 8))

    def test_findBreak_2(self):
        data = [6,0,5,0,6,0,8,2,4,0,6,0,9,0,15,6,10,8]
        ccs = ph.calculatePeakPersistentHomology(data)
        actual_levels = np.unique([cc.lifetime() for cc in ccs]).tolist()
        expected_levels = [2, 4, 5, 6, 8, 9, 15]
        self.assertListEqual(actual_levels, expected_levels)
        bounds = ph.findBreak(ccs)
        self.assertEqual(bounds, (9, 15))


if __name__ == '__main__':
    unittest.main()
