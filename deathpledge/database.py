"""
Writes JSON files to the IBM Cloudant database

For inspiration/a working example:
    https://github.com/IBM-Cloud/get-started-python

IBM's docs:
    https://cloud.ibm.com/docs/services/Cloudant/tutorials?topic=cloudant-getting-started-with-cloudant
    https://cloud.ibm.com/docs/Cloudant?topic=cloudant-http

Cloudant's docs:
    https://python-cloudant.readthedocs.io/en/stable/modules.html

"""

from cloudant.client import Cloudant
from cloudant.result import Result
from time import sleep
import logging

import deathpledge
from deathpledge import keys

logger = logging.getLogger(__name__)


class DatabaseClient(object):
    """A context manager to create a session with my Cloudant database via IAM."""
    def __init__(self):
        self.account_name = keys['Cloudant_creds']['username']
        self.api_key = keys['Cloudant_creds']['apikey']

    def __enter__(self):
        self._cloudant_session = Cloudant.iam(self.account_name, self.api_key)
        self._cloudant_session.connect()
        return self._cloudant_session

    def __exit__(self, exc_type, exc_value, traceback):
        self._cloudant_session.disconnect()


def push_one_to_db(doc, db_name, client):
    """Upload single doc to database.

    If doc id is already in database, get current _rev and add to doc so that the
    database will accept the updated document and increment the revision.

    Args:
        doc (Home): Home instance to be uploaded.
        db_name (str): Database to upload to.
        client (Cloudant.iam): Connection to Cloudant.

    Returns: HTTP response

    """
    try:
        db = client[db_name]
    except KeyError:
        logger.error(f"Database '{db_name}' does not exist!")
        raise

    # Create or update the document
    get_rev_id_for_doc(local_doc=doc, db=db)

    end_point = f'{client.server_url}/{db_name}/{doc.docid}'
    r = client.r_session.put(url=end_point, json=doc)
    if r.status_code not in [200, 201]:
        logger.error(f'Document creation failed. Response: {r}: {r.text}')
    sleep(1)
    return


def get_rev_id_for_doc(local_doc, db):
    """Checks if doc is in db and gets rev id."""
    try:
        remote_doc = db[local_doc.docid]
    except KeyError:
        logger.info(f"No document in database for {local_doc['full_address']}")
        try:
            del local_doc['_rev']
        except KeyError:
            pass
    else:
        logger.info(f"Document for {local_doc['full_address']} exists, updating with new revision")
        local_doc['_rev'] = remote_doc['_rev']


def check_for_doc(doc_id, db_name, client):
    """Boolean check for existing doc."""
    return doc_id in client[db_name]


def get_single_doc(doc_id, db_name, client):
    """Fetch a doc from the database."""
    db = client[db_name]
    try:
        doc = db[doc_id]
        logger.info(f'Fetched document {doc_id} from {db_name}')
    except KeyError:
        logger.exception(f'Could not find doc_id {doc_id} in {db_name}')
        raise
    return doc


def get_bulk_docs(doc_ids: list, db_name: str, client: Cloudant.iam) -> dict:
    """Fetch multiple docs from the database."""
    db = client[db_name]
    result = db.all_docs(keys=doc_ids, include_docs=True)
    raw_rows = result['rows']
    rows_by_docid = {x['id']: x for x in raw_rows if not x.get('error')}
    return rows_by_docid


def get_url_list(client):
    """Get all docs from URL view, for filling in Google sheet."""
    db = client[deathpledge.RAW_DATABASE_NAME]
    ddoc_id = '_design/simpleViews'
    view_name = 'urlList'
    results = db.get_view_result(ddoc_id, view_name, raw_result=True, include_docs=False)
    # Turn into dict of {index: <home data>} for easier dataframing
    results = {i: x['key'] for i, x in enumerate(results['rows'])}
    return results


def get_doc_list(client: Cloudant.iam, db_name: str) -> list:
    db = client[db_name]
    result_collection = Result(db.all_docs, include_docs=False)
    return [*result_collection]


def bulk_upload(docs: list, db_name: str, client: Cloudant.iam):
    db = client[db_name]
    db.bulk_docs(docs)
