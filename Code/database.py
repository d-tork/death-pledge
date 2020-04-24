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
from cloudant.document import Document  # Context manager
from time import sleep, localtime, strftime
from os import path
import pandas as pd
import json
import logging
from datetime import datetime

import Code
from Code.api_calls.keys import db_creds

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
    with cloudant_iam(db_creds['username'], db_creds['apikey']) as client:
        # Access the database
        try:
            db = client[db_name]
            print(f"\nConnected to database '{db_name}'")
        except KeyError:
            db = client.create_database(db_name, partitioned=False)
            if db.exists():
                print(f"'{db_name}' successfully created.\n")

        # Create or update the document
        if replace_or_create(doc, db):
            end_point = f'{client.server_url}/{db_name}/{doc.docid}'
            r = client.r_session.put(url=end_point, json=doc)
            if r.status_code not in [200, 201]:
                print(f'Document creation failed.\n\tResponse: {r}: {r.text}')
                raise FailedUpload(f'Document creation failed with code {r.status_code}')
        else:
            print('\t no changes pushed to database.')
            logger.info(f'{doc.docid}: no changes pushed to database.')
    sleep(1)
    return


def bulk_upload(doclist, db_name):
    """Push multiple docs for creation or update.

    For some silly-ass reason, the python API for ``bulk_docs()`` refuses any
    request, says it has to be a POST request. So the bulk upload is re-built
    as data for the POST request.

    Args:
        doclist (list): Array of home instances.
        db_name (str): Database to upload to.

    Returns: None
    """

    def bulk_upload_post_request():
        """Sends bulk data to db using established client session.

        Returns: HTTP response
        """
        post_data = {'docs': doclist}
        end_point = f'{client.server_url}/{db_name}/_bulk_docs'
        headers = {  # supported headers in Cloudant, but usually not necessary
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Content-Encoding': '',  # gzip or deflate
            'If-None-Match': '',  # optional
        }
        r = client.r_session.post(url=end_point, json=post_data)
        return r

    def write_response_to_file():
        outpath = path.join(Code.PROJ_PATH, 'Data', 'bulk_upload_status.log')
        with open(outpath, 'a') as f:
            f.writelines([
                '#' * 5,
                f"\n{strftime('%d %b %Y %H:%M:%S', localtime())} - {db_name}\n",
                '#' * 5 + '\n',
                ])
            if len(df_failures.index) > 0:
                f.writelines(['\n', '#' * 3, f"\n Upload Errors \n", '#' * 3, '\n'])
                f.write(df_failures.to_string())
                f.write('\n')
            json.dump(resp.json(), f, indent=2)
            f.writelines(['\n', '#' * 25, '\n' * 2])
        return

    def verify_bulk_upload():
        """Checks if all docs made it to the database.

        Returns: DataFrame
            Docs that encountered errors. Can be an empty dataframe.

        """
        if resp.status_code not in [200, 201]:
            print('Bulk POST request failed.')
        else:
            print('Bulk POST request succeeded.')
        # Turn doc statuses into dataframe
        df = pd.json_normalize(resp.json())
        # Add some metadata for appending
        df['database'] = db_name
        df['timestamp'] = pd.to_datetime(datetime.now())

        # Save status of all docs pushed
        outpath = path.join(Code.PROJ_PATH, 'Data', 'bulk_upload_all.csv')
        df = df.reindex(columns=['timestamp', 'database', 'ok', 'id', 'rev', 'error', 'reason'])
        df.to_csv(outpath, mode='a', index=True)
        return df.loc[df['ok'].isna()]

    def retry_bulk_failed():
        """Call the upload() method on individual listings that failed."""
        # Get only the docs that failed
        filtered_doclist = [doc for doc in doclist if doc['_id'] in df_failures['id']]

        for doc in filtered_doclist:
            doc.upload(db_name)
        return

    # Retrieve the revision IDs for existing docs so they can be updated
    with cloudant_iam(db_creds['username'], db_creds['apikey']) as client:
        try:
            db = client[db_name]
            print(f"\nConnected to database '{db_name}'")
        except KeyError:
            print(f'Database {db_name} does not exist!')
            raise

        remote_doclist = db.all_docs(
            include_docs=False,
            keys=[doc['_id'] for doc in doclist]  # only check for docs I'm pushing
        )['rows']
        # Create a mapping of id to rev
        id_rev_mapping = {
            doc['id']: doc['value']['rev']
            for doc in remote_doclist
            if not doc.get('error')  # error key exists when doc id is not found
        }
        # Add the current _rev to my local docs about to be pushed
        for doc in doclist:
            if doc['_id'] in id_rev_mapping:
                doc['_rev'] = id_rev_mapping.get(doc['_id'])
            else:
                try:
                    del doc['_rev']
                except KeyError:
                    pass

        resp = bulk_upload_post_request()

    # Check that all docs made it
    df_failures = verify_bulk_upload()
    print(f'Upload failures: {len(df_failures.index)}')

    if len(df_failures.index) > 0:
        retry_bulk_failed()

    # Dump results
    write_response_to_file()
    return


def replace_or_create(local_doc, db):
    """Checks if doc is in db and if new version is different.

    Returns: bool
        True: If the new doc has valid changes (other than a different scraped
    time), replace. If the doc id is not yet in the database, create.
        False: No difference between remote and local doc.

    """
    if local_doc.docid in db:
        # Retrieve remote doc and make carbon copy without scrape_data and _rev
        remote_doc = db[local_doc.docid]
        exclude_keys = ['scrape_data', '_rev']
        remote_compare = {k: v for k, v in remote_doc.items() if k not in exclude_keys}
        local_compare = {k: v for k, v in local_doc.items() if k not in exclude_keys}

        if remote_compare == local_compare:
            return False
        print(f'Document for {local_doc.full_address} exists, updating with new revision')
        local_doc['_rev'] = remote_doc['_rev']
        return True
    print(f'Creating document for {local_doc.full_address}')
    return True




