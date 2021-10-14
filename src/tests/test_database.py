import unittest
from server import Database

class DatabaseTest(unittest.TestCase):
    def test_db_uri_1(self):
        actual = Database.db_uri('path with space', 'file.db')
        self.assertEqual(actual, 'sqlite:////path with space/file.db')

    def test_db_uri_2(self):
        actual = Database.db_uri('/path with space', 'file.db')
        self.assertEqual(actual, 'sqlite:////path with space/file.db')

    def test_db_uri_3(self):
        actual = Database.db_uri('c:\\path with space', 'file.db')
        self.assertEqual(actual, 'sqlite:///c:/path with space/file.db')


if __name__ == '__main__':
    unittest.main()
