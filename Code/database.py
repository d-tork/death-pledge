"""
Writes JSON files to the IBM Cloudant database

For inspiration/a working example:
    https://github.com/IBM-Cloud/get-started-python

IBM's docs:
    https://cloud.ibm.com/docs/services/Cloudant/tutorials?topic=cloudant-getting-started-with-cloudant

Cloudant's docs:
    https://python-cloudant.readthedocs.io/en/stable/modules.html

"""

from cloudant.client import Cloudant
from time import sleep

from Code.api_calls.keys import db_creds


def push_to_db(doc):
    # Establish connection to service instance
    client = Cloudant.iam(db_creds['username'], db_creds['apikey'])
    client.connect()

    databaseName = 'deathpledge_raw'
    try:
        myDatabase = client[databaseName]
        print(f"Connected to database '{databaseName}'\n")
    except KeyError:
        myDatabase = client.create_database(databaseName, partitioned=False)
        if myDatabase.exists():
            print(f"'{databaseName}' successfully created.\n")

    try:
        newDocument = myDatabase.create_document(doc, throw_on_exists=True)
        if newDocument.exists():
            print('Document created.')
    except Exception as e:
        print(f'Document creation failed.\n{e}')
    sleep(1)

    client.disconnect()
    raise(Exception)

