
import unittest
from deathpledge.api_calls import google_sheets


class UrlDataframeTestCase(unittest.TestCase):

    def test_trim_url(self):
        sample_long_url = 'https://daniellebiegner.realscout.com/homesearch/listings/matched/p-2418-foster-pl-temple-hills-20748-brightmls-84?auth_token=Whedxn8uPXU3M95a9u_q&utm_source=property_alert&utm_medium=email&utm_campaign=homebuyer'
        sample_trimmed_url = 'https://daniellebiegner.realscout.com/homesearch/listings/matched/p-2418-foster-pl-temple-hills-20748-brightmls-84'
        self.assertEqual(google_sheets.trim_url(sample_long_url), sample_trimmed_url)


if __name__ == '__main__':
    unittest.main()
