from util import persistent_homology as ph
import unittest

class PersistentHomologyTest(unittest.TestCase):
    def test_PeakPersistentHomology(self):
        data = [30, 29, 41, 4, 114, 1, 3, 2, 33, 9, 112, 40, 118]
        ccs = ph.calculatePeakPersistentHomology(data)
        ccs = ph.sortByLifetime(ccs)
        self.assertEqual(str(ccs), '[(12, 118) -> (5, 1), (4, 114) -> (5, 1), (10, 112) -> (11, 40), (2, 41) -> (3, 4), (8, 33) -> (9, 9), (0, 30) -> (1, 29), (6, 3) -> (7, 2)]')

if __name__ == '__main__':
    unittest.main()
