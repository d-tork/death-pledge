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
import requests
from urllib import parse
import pandas as pd
import json
import logging
from datetime import datetime

import Code
from Code.api_calls.keys import db_creds

logger = logging.Logger(__name__)


def push_one_to_db(doc, db_name):
    # Establish connection to service instance
    with cloudant_iam(db_creds['username'], db_creds['apikey']) as client:
        # Access the database
        try:
            db = client[db_name]
            print(f"Connected to database '{db_name}'\n")
        except KeyError:
            db = client.create_database(db_name, partitioned=False)
            if db.exists():
                print(f"'{db_name}' successfully created.\n")

        # Create or update the document
        if replace_or_create(doc, db):
            try:
                end_point = f'{client.server_url}/{db_name}/{doc.docid}'
                r = client.r_session.post(url=end_point, json=doc)
            except Exception as e:
                print(f'Document creation failed.\n\tResponse: {r}: {r.text}')
                raise
        else:
            logger.info(f'{doc.docid}: no changes pushed to database.')
    sleep(1)


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
        outpath = path.join(Code.PROJ_PATH, 'Data', 'bulk_upload_status.txt')
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
        df.to_csv(outpath, mode='a', header=False, index=False)
        return df.loc[df['ok'].isna()]

    def retry_bulk_failed(doclist, df_failures, db_name):
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
            print(f"Connected to database '{db_name}'\n")
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
    df_failures = verify_bulk_upload(resp, db_name)
    print(f'Upload failures: {len(df_failures.index)}')

    if len(df_failures.index) > 0:
        retry_bulk_failed(doclist, df_failures, db_name)

    # Dump results
    write_response_to_file(resp, df_failures, db_name)
    return


def write_response_to_file(r, df_failures, db_name):
    outpath = path.join(Code.PROJ_PATH, 'Data', 'bulk_upload_status.txt')
    with open(outpath, 'a') as f:
        f.writelines([
            '#' * 5,
            f"\n{strftime('%d %b %Y %H:%M:%S', localtime())} - {db_name}\n",
            '#' * 5 + '\n',
            ])
        if len(df_failures.index) > 0:
            f.writelines(['\n', '#'*3, f"\n Upload Errors \n", '#'*3, '\n'])
            f.write(df_failures.to_string())
            f.write('\n')
        json.dump(r.json(), f, indent=2)
        f.writelines(['\n', '#'*25, '\n'*2])


def post_bulk_upload(doclist, db_name):
    post_data = {'docs': doclist}
    post_url = parse.urlunparse(
        # (scheme, netloc, path, params, query, fragment)
        ('https', db_creds['host'], f'/{db_name}/_bulk_docs', '', '', '')
    )
    headers = {  # supported headers in Cloudant, but usually not necessary
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Content-Encoding': '',  # gzip or deflate
        'If-None-Match': '',     # optional
    }
    r = requests.post(
        url=post_url,
        auth=(db_creds['username'], db_creds['password']),
        json=post_data
    )
    return r


def verify_bulk_upload(r, db_name):
    """Checks if all docs made it to the database.

    Args:
        r (Response): Response from request.
        db_name (str): Database name (for adding to dataframe)

    Returns: DataFrame
        Docs that encountered errors. Can be an empty dataframe.

    """
    if r.status_code not in [200, 201]:
        print('Bulk POST request failed.')
    else:
        print('Bulk POST request succeeded.')
    # Turn doc statuses into dataframe
    df = pd.json_normalize(r.json())
    # Add some metadata for appending
    df['database'] = db_name
    df['timestamp'] = pd.to_datetime(datetime.now())

    # Save status of all docs pushed
    outpath = path.join(Code.PROJ_PATH, 'Data', 'bulk_upload_all.csv')
    df = df.reindex(columns=['timestamp', 'database', 'ok', 'id', 'rev', 'error', 'reason'])
    df.to_csv(outpath, mode='a', header=False, index=False)
    return df.loc[df['ok'].isna()]


def retry_bulk_failed(doclist, df_failures, db_name):
    """Call the upload() method on individual listings that failed."""
    # Get only the docs that failed
    filtered_doclist = [doc for doc in doclist if doc['_id'] in df_failures['id']]

    for doc in filtered_doclist:
        doc.upload(db_name)





