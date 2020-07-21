
import unittest
import os
import pickle
import pandas as pd

from deathpledge.api_calls import google_sheets


class UrlDataframeTestCase(unittest.TestCase):

    def test_trim_url(self):
        sample_long_url = 'https://daniellebiegner.realscout.com/homesearch/listings/matched/p-2418-foster-pl-temple-hills-20748-brightmls-84?auth_token=Whedxn8uPXU3M95a9u_q&utm_source=property_alert&utm_medium=email&utm_campaign=homebuyer'
        sample_trimmed_url = 'https://daniellebiegner.realscout.com/homesearch/listings/matched/p-2418-foster-pl-temple-hills-20748-brightmls-84'
        self.assertEqual(google_sheets.trim_url(sample_long_url), sample_trimmed_url)


class ExistingGoogleCredentialsTestCase(unittest.TestCase):
    def setUp(self):
        sample_contents = {'valid': True}
        self.sample_pickle_filepath = os.path.join(google_sheets.DIRPATH, 'sample.pickle')
        with open(self.sample_pickle_filepath, 'wb') as f:
            pickle.dump(sample_contents, f)

    def test_get_existing_creds(self):
        existing_token = google_sheets.get_existing_token(self.sample_pickle_filepath)
        self.assertIsInstance(existing_token, dict)

    def tearDown(self):
        os.remove(self.sample_pickle_filepath)


@unittest.skip('Makes call to internet')
class GoogleDataFrameTestCase(unittest.TestCase):
    def setUp(self):
        self.sample_creds = google_sheets.get_creds()

    def test_google_response_has_values(self):
        rows = google_sheets.get_google_sheets_rows(self.sample_creds)
        self.assertIsInstance(rows, list)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
