
import unittest
import pandas as pd

from deathpledge.api_calls import google_sheets as gs


class URLDataFrameClassTestCase(unittest.TestCase):
    def setUp(self):
        self.header = ['added_date', 'status', 'url', 'ml_number', 'full_address', 'docid', 'comments']
        self.data = ['5/3/2019', 'Closed', 'www.sample.com?query=hi', 'MDPG10001', '867 North maple', 'abc12def', None]
        self.df = pd.DataFrame(data=[self.header, self.data])

    def test_field_name_in_column_headers(self):
        urls = gs.URLDataFrame(self.df)
        self.assertIn(self.header[2], urls.columns)

    def test_no_null_urls(self):
        urls = gs.URLDataFrame(self.df)
        null_url_count = urls.df['url'].isna().sum()
        self.assertEqual(null_url_count, 0)

    def test_no_params_in_urls(self):
        urls = gs.URLDataFrame(self.df)
        url = urls.df['url'].iloc[0]
        q_mark_location = url.find('?')
        self.assertEqual(q_mark_location, -1)


class UrlTrimmerTestCase(unittest.TestCase):
    """Checks if URL can be trimmed of junk and "matched" removed."""
    def setUp(self):
        self.normal_url = 'https://sub.domain.com/hs/lis/p-867-n-maple-brightmls-574'
        self.matched_url = 'https://sub.domain.com/hs/lis/matched/p-867-n-maple-brightmls-574'
        self.query_url = 'https://sub.domain.com/hs/lis/matched/p-867-n-maple-brightmls-574?utm=hb'

    def test_matched_removed(self):
        url_without_matched = gs.URLDataFrame.trim_url(self.matched_url)
        self.assertNotIn('matched', url_without_matched)

    def test_query_removed(self):
        url_without_query = gs.URLDataFrame.trim_url(self.query_url)
        self.assertNotIn('?utm=', url_without_query)

    def test_normal_untouched(self):
        url_unchanged = gs.URLDataFrame.trim_url(self.normal_url)
        self.assertEqual(url_unchanged, self.normal_url)


if __name__ == '__main__':
    unittest.main()
