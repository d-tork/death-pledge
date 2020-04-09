"""
Writes JSON files to the IBM Cloudant database

For inspiration/a working example:
    https://github.com/IBM-Cloud/get-started-python

IBM's docs:
    https://cloud.ibm.com/docs/services/Cloudant/tutorials?topic=cloudant-getting-started-with-cloudant

Cloudant's docs:
    https://python-cloudant.readthedocs.io/en/stable/modules.html

"""

from cloudant import cloudant_iam
from cloudant.document import Document
from time import sleep

from Code.api_calls.keys import db_creds


def push_one_to_db(doc):
    # Establish connection to service instance
    with cloudant_iam(db_creds['username'], db_creds['apikey']) as client:
        # Access the database
        databaseName = 'deathpledge_raw'
        try:
            myDatabase = client[databaseName]
            print(f"Connected to database '{databaseName}'\n")
        except KeyError:
            myDatabase = client.create_database(databaseName, partitioned=False)
            if myDatabase.exists():
                print(f"'{databaseName}' successfully created.\n")

        # Create or update the document
        if doc.docid in myDatabase:
            print(f'Document for {doc.address} exists, updating with new revision')
            with Document(myDatabase, doc.docid) as remote_doc:
                remote_doc.update(doc)
        else:
            try:
                myDatabase.create_document(doc, throw_on_exists=True)
                print(f'Document created for {doc.address}')
            except Exception as e:
                print(f'Document creation failed.\n{e}')
                raise
        sleep(1)
