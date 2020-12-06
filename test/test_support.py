import unittest

from deathpledge import support


class AddressTestCase(unittest.TestCase):
    def setUp(self):
        self.full_address = '5065 7TH RD S #202 ARLINGTON, VA 22204'

    def test_clean_address(self):
        actual = support.clean_address(self.full_address)
        expected = '5065 7TH RD S 202 ARLINGTON VA 22204'
        self.assertEqual(actual, expected)

    def test_create_filename_from_addr(self):
        actual = support.create_filename_from_addr(self.full_address)
        expected = '5065_7TH_RD_S_202_ARLINGTON_VA_22204.json'
        self.assertEqual(actual, expected)

    def test_create_house_id(self):
        actual = support.create_house_id(self.full_address)
        expected = '1437f8a6674882e58289a1a744f46a77cd4deb48'
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
