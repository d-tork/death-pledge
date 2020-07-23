
import unittest
import os
import pandas as pd

from deathpledge import scrape2


class HomesWithRawDataTestCase(unittest.TestCase):
    def setUp(self):
        header = ['added_date', 'status', 'url', 'ml_number', 'full_address', 'docid', 'comments']
        data = ['5/3/2019', 'Active', 'www.sample.com', 'MDPG10001', '867 North maple', 'abc12def',
                     None]
        self.df = pd.DataFrame(data=[header, data])

    def test_add_(self):

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
