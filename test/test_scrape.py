
import unittest
import os
import pandas as pd

from deathpledge import scrape2


class SeleniumDriverTestCase(unittest.TestCase):
    def test_print_geckodriver_version(self):
        with scrape2.SeleniumDriver() as sd:
            self.assertIsInstance(sd.geckodriver_version, str)


if __name__ == '__main__':
    unittest.main()
