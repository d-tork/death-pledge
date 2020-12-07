import unittest
from deathpledge import realscout as rs
from deathpledge.scrape2 import SeleniumDriver

import bs4


class RealScoutWebsiteTestCase(unittest.TestCase):
    def setUp(self):
        self.driver = SeleniumDriver().webdriver
        self.website = rs.RealScoutWebsite(self.driver)

    def test_realscout_is_configured(self):
        self.assertIn('sign_in_url', self.website._config)
        self.assertIn('email', self.website._config)
        self.assertIn('password', self.website._config)

    def test_website_sign_in_successful(self):
        self.website.sign_into_website()
        self.assertTrue(self.website.signed_in)

    def test_bad_url_raises_error(self):
        with self.assertRaises(ValueError):
            self.website.get_soup_for_url('https://google.com/thispagedoesnotexist')

    def test_get_soup_from_url(self):
        sample_url = self.website._config.get('sample_url')
        soup = self.website.get_soup_for_url(url=sample_url)
        self.assertIsInstance(soup, bs4.BeautifulSoup)

    def tearDown(self):
        self.driver.quit()


if __name__ == '__main__':
    unittest.main()
