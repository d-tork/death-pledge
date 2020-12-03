import unittest
import pandas as pd

import deathpledge
from deathpledge import database


class BulkFetchDocsTestCase(unittest.TestCase):
    sample_docids = ['dcc18a6fd9aee31922376a8263ae795d317126fa',
                     '3af1b97a895162cbf729ddf7a828e4ec476df151']

    def setUp(self):
        self.multiple_docs = database.get_bulk_docs(
            db_name=deathpledge.RAW_DATABASE_NAME,
            doc_ids=self.sample_docids
        )

    def test_bulk_gets_list(self):
        self.assertIsInstance(self.multiple_docs, list)

    def test_bulk_gets_multiple(self):
        number_of_returned_docs = len(self.multiple_docs)
        self.assertGreater(number_of_returned_docs, 1)

    def test_member_of_result_is_dict(self):
        a_result = self.multiple_docs[0]
        self.assertIsInstance(a_result, dict)


if __name__ == '__main__':
    unittest.main()
