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
from tqdm import tqdm

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
    raw_rows = rate_limit_pull(result['rows'], est_doc_count=len(doc_ids))
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


def get_doc_list(client: Cloudant.iam, db_name: str, **kwargs) -> list:
    db = client[db_name]
    result_collection = Result(db.all_docs, include_docs=False)
    return [*rate_limit_pull(result_collection, **kwargs)]


def bulk_fetch_raw_docs(urls, db_client) -> dict:
    """Get the requested houses from the raw database."""
    fetched_docs = get_bulk_docs(
        doc_ids=urls['docid'].tolist(),
        db_name=deathpledge.RAW_DATABASE_NAME,
        client=db_client
    )
    flattened = {k: fetched_docs[k]['doc'] for k, v in fetched_docs.items()}
    for docid, doc in flattened.items():
        try:
            del doc['_rev']
        except KeyError:
            continue
    return flattened


def get_active_doc_ids(client: Cloudant.iam, db_name: str, **kwargs) -> dict:
    """Get docids where status is not some form of closed.

    Returns:
        dict: Mapping of docid to doc

    """
    db = client[db_name]
    selector = {
        'doctype': 'home',
        'status': {'$in': [
            'Active',
            'Pending',
            'Active Under Contract',
            'ACTIVE',
            'PENDING',
            'ACTIVE UNDER CONTRACT',
        ]}
    }
    query_results = db.get_query_result(selector=selector, fields=['_id', '_rev'])
    docs = {result['_id']: result for result in rate_limit_pull(query_results, **kwargs)}
    return docs


def bulk_upload(docs: list, db_name: str, client: Cloudant.iam):
    """Push an array of docs to the database.

    Documents _must_ have an ``_id`` field (and possibly a ``_rev`` field if
    it's being updated).

    """
    for doc in docs:
        try:
            doc['_id'] = doc.docid
        except AttributeError:
            continue
    db = client[db_name]
    resp = []
    for part in rate_limit_push(docs=docs):
        part_resp = db.bulk_docs(part)
        resp.extend(part_resp)
    get_successful_uploads(resp, db_name=db_name)


def rate_limit_push(docs: list) -> list:
    """Slow the calls to Cloudant in order to not exceed write limit."""
    doc_count = len(docs)
    iterations = int(doc_count / 20) + 1
    start = 0
    for i in tqdm(range(iterations)):
        stop = start + 20
        partition = [x for x in docs[start:stop]]
        start = stop
        sleep(1)
        yield partition


def rate_limit_pull(docs: list, est_doc_count: int = 1000) -> list:
    """Slow the calls to Cloudant in order to not exceed read limit."""
    iterations = int(est_doc_count / 20) + 1
    start = 0
    all_docs = []
    for i in tqdm(range(iterations)):
        stop = start + 20
        partition = [x for x in docs[start:stop]]
        all_docs.extend(partition)
        start = stop
        sleep(1)
    return all_docs


def get_successful_uploads(resp: list, db_name: str):
    """Count how many docs were created out of how many attempted."""
    attempted_count = len(resp)
    successful = [i['id'] for i in resp if i.get('ok')]
    logger.info(f'Created the following docs in {db_name}:')
    logger.info(f'\t{successful}')
    logger.info(f'{len(successful)}/{attempted_count} docs created')


def delete_bad_docs(id_prefix: str, db_name: str):
    """Delete docs which received a bad doc_id."""
    with DatabaseClient() as cloudant:
        db = cloudant[db_name]
        response = db.all_docs(include_docs=False)
        all_docs = rate_limit_pull(response['rows'], est_doc_count=775)
        docs_to_delete = [x for x in all_docs if x['id'].startswith(id_prefix)]
        proceed = input(f'{len(docs_to_delete)} will be deleted: ')
        for part in rate_limit_push(docs_to_delete):
            for doc in part:
                db[doc['id']].delete()
                sleep(1)
