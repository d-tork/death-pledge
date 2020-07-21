
import unittest
import os
import pickle
import pandas as pd

from deathpledge.api_calls import google_sheets


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
class GoogleAPITestCase(unittest.TestCase):
    def setUp(self):
        self.sample_creds = google_sheets.get_creds()

    def test_google_response_has_values(self):
        rows = google_sheets.get_google_sheets_rows(self.sample_creds)
        self.assertIsInstance(rows, list)

    def tearDown(self):
        pass


class URLDataFrameClassTestCase(unittest.TestCase):
    def setUp(self):
        self.header = ['added_date', 'status', 'url', 'ml_number', 'full_address', 'docid', 'comments']
        self.data = ['5/3/2019', 'Closed', 'www.sample.com?query=hi', 'MDPG10001', '867 North maple', 'abc12def', None]
        self.df = pd.DataFrame(data=[self.header, self.data])

    def test_field_name_in_column_headers(self):
        urls = google_sheets.URLDataFrame(self.df)
        self.assertIn(self.header[2], urls.columns)

    def test_no_null_urls(self):
        urls = google_sheets.URLDataFrame(self.df)
        null_url_count = urls.df['url'].isna().sum()
        self.assertEqual(null_url_count, 0)

    def test_no_params_in_urls(self):
        urls = google_sheets.URLDataFrame(self.df)
        url = urls.df['url'].iloc[0]
        q_mark_location = url.find('?')
        self.assertEqual(q_mark_location, -1)

    def test_split_for_scrape(self):
        urls_not_all_forced = google_sheets.URLDataFrame(self.df, force_all=False)
        len_to_scrape_should_be_zero = len(urls_not_all_forced.rows_to_scrape)
        len_not_to_scrape_should_be_one = len(urls_not_all_forced.rows_not_to_scrape)
        self.assertEqual(len_to_scrape_should_be_zero, 0)
        self.assertEqual(len_not_to_scrape_should_be_one, 1)

    def test_force_all_rescrapes(self):
        urls_all_forced = google_sheets.URLDataFrame(self.df, force_all=True)
        len_to_scrape_should_be_one = len(urls_all_forced.rows_to_scrape)
        self.assertEqual(len_to_scrape_should_be_one, 1)


if __name__ == '__main__':
    unittest.main()
