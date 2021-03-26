import unittest
from deathpledge import cleaning


class FeeTestCase(unittest.TestCase):
    def setUp(self):
        self.home = {}

    def test_split_condo_fee_with_freq(self):
        condo_field = 'condocoop_fee'
        self.home[condo_field] = '295.16/Monthly'
        cleaning.split_fee_frequency(self.home)
        expected_fee = 295.16
        expected_freq = 'Monthly'
        self.assertEqual(self.home.get(condo_field), expected_fee)
        self.assertEqual(self.home.get(f'{condo_field}_frequency'), expected_freq)

    def test_split_condo_fee_currency(self):
        condo_field = 'condocoop_fee'
        self.home[condo_field] = '$410'
        cleaning.split_fee_frequency(self.home)
        expected_fee = 410
        self.assertEqual(expected_fee, self.home.get(condo_field))


if __name__ == '__main__':
    unittest.main()
