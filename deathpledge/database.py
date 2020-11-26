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

from cloudant import cloudant_iam       # Context manager
from time import sleep
import logging

import deathpledge
from deathpledge import keys

logger = logging.getLogger(__name__)


class FailedUpload(Exception):
    """For a bad HTTP response code, but nothing wrong with the module."""
    pass


def push_one_to_db(doc, db_name):
    """Upload single doc to database.

    If doc id is already in database, compares the contents of the home
    dictionary to the remote copy (excluding the scrape_data sub-dict,
    since the scraped date is guaranteed to be different).

    If there are no differences, it skips the upload. If there are any
    differences, the _rev gets added so that the database will accept the
    updated document and increment the revision.

    Args:
        doc (Home): Home instance to be uploaded.
        db_name (str): Database to upload to.

    Returns: HTTP response

    """
    # Establish connection to service instance
    with cloudant_iam(keys['Cloudant_creds']['username'], keys['Cloudant_creds']['apikey']) as client:
        try:
            db = client[db_name]
            print(f"\nConnected to database '{db_name}'")
        except KeyError:
            db = client.create_database(db_name, partitioned=False)
            if db.exists():
                print(f"'{db_name}' successfully created.\n")

        # Create or update the document
        end_point = f'{client.server_url}/{db_name}/{doc.docid}'
        r = client.r_session.put(url=end_point, json=doc)
        if r.status_code not in [200, 201]:
            logger.error(f'Document creation failed. Response: {r}: {r.text}')
            raise FailedUpload(f'Document creation failed with code {r.status_code}')
    sleep(1)
    return


def get_rev_id_for_doc(local_doc, db):
    """Checks if doc is in db and gets rev id if it is."""
    try:
        remote_doc = db[local_doc.docid]
        local_doc['_rev'] = remote_doc['_rev']
    except KeyError:
        logger.info(f'No document in database for {local_doc.full_address}')
    else:
        logger.info(f'Document for {local_doc.full_address} exists, updating with new revision')
    finally:
        return local_doc


def check_for_doc(db_name, doc_id):
    """Boolean check for existing doc."""
    with cloudant_iam(keys['Cloudant_creds']['username'], keys['Cloudant_creds']['apikey']) as client:
        doc_exists = doc_id in client[db_name]
    return doc_exists


def is_closed(db_name, doc_id):
    """Boolean check for whether listing is already sold."""
    with cloudant_iam(keys['Cloudant_creds']['username'], keys['Cloudant_creds']['apikey']) as client:
        db = client[db_name]
        if doc_id in db:
            doc = db[doc_id]
            return doc['listing']['status'] == 'Closed'
        else:
            return False


def get_single_doc(db_name, doc_id):
    """Fetch a doc from the database."""
    with cloudant_iam(keys['Cloudant_creds']['username'], keys['Cloudant_creds']['apikey']) as client:
        # Access the database
        try:
            db = client[db_name]
        except KeyError:
            logger.exception(f'Could not connect to {db_name}.')

        try:
            doc = db[doc_id]
            logger.info(f'Fetched document {doc_id}')
        except KeyError:
            logger.exception(f'Could not find doc_id {doc_id}')
    return doc


def get_url_list():
    """Get all docs from URL view, for filling in Google sheet."""
    with cloudant_iam(keys['Cloudant_creds']['username'], keys['Cloudant_creds']['apikey']) as client:
        db = client[deathpledge.RAW_DATABASE_NAME]
        ddoc_id = '_design/simpleViews'
        view_name = 'urlList'
        results = db.get_view_result(ddoc_id, view_name, raw_result=True, include_docs=False)
    # Turn into dict of {index: <home data>} for easier dataframing
    results = {i: x['key'] for i, x in enumerate(results['rows'])}
    return results


