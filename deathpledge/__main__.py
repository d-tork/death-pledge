"""Run actions on housing search spreadsheet."""
from os import path
import argparse
import logging

import deathpledge
from deathpledge.logs.log_setup import setup_logging
from deathpledge.logs import *
from deathpledge.api_calls import google_sheets as gs, check
from deathpledge import classes, scrape2, support, database

logger = logging.getLogger(__name__)


@support.timing
def main():
    logging_config = path.join(deathpledge.PROJ_PATH, 'config', 'logging.yaml')
    setup_logging(config_path=logging_config)

    args = parse_commandline_arguments()
    google_creds = gs.GoogleCreds(
        token_path=path.join(deathpledge.CONFIG_PATH, 'token.pickle'),
        creds_path=path.join(deathpledge.CONFIG_PATH, 'oauth_client_id.json')
    ).creds

    with database.DatabaseClient() as cloudant:
        if not args.process_only:
            check_and_scrape_homescout(db_client=cloudant, max_pages=5, quiet=True)
            gs.refresh_url_sheet(google_creds, db_client=cloudant)
        process_data(args, google_creds, db_client=cloudant)
    return


def parse_commandline_arguments():
    parser = argparse.ArgumentParser(
        description="""Run the deathpledge app on URLs in the Google sheet 'House
        decision matrix'. Scrapes, uploads to the raw database, cleans, enriches,
        and then uploads to the clean database.""",
        epilog='Using --force-all overrides --new.'
    )
    parser.add_argument('-n', default=None, type=int, dest='last_n',
                        help='Number of recent URLs to parse, starting from the bottom of the list.')
    parser.add_argument('--process', action='store_true', dest='process_only',
                        help='Only process listings already in the raw db.')
    return parser.parse_args()


def check_and_scrape_homescout(db_client, **kwargs):
    scrape2.scrape_from_homescout_gallery(db_client=db_client, **kwargs)


def get_urls_to_scrape(urls):
    """Split off url rows that are either still open or don't exist in database."""
    status_open = urls.df['status'] != 'Closed'
    not_in_db = urls.df['docid'].isna()
    return urls.df.loc[status_open | not_in_db]


def process_data(args, google_creds, db_client):
    urls = gs.get_url_dataframe(google_creds, last_n=args.last_n)
    fetched_raw_docs = bulk_fetch_raw_docs(urls, db_client)
    for row in urls.itertuples():
        if row.docid in db_client[deathpledge.DATABASE_NAME]:
            continue
        doc = next((d for d in fetched_raw_docs if d['id'] == row.docid))['doc']
        home = classes.Home(
            url=doc['url'],
            added_date=doc['added_date'],
            docid=doc['_id']
        )
        home.update(doc)
        home.clean()
        home.enrich()
        home.upload(db_name=deathpledge.DATABASE_NAME, db_client=db_client)


def bulk_fetch_raw_docs(urls, db_client):
    """Get the requested houses from the raw database."""
    fetched_docs = database.get_bulk_docs(
        doc_ids=urls.df['docid'].tolist(),
        db_name=deathpledge.RAW_DATABASE_NAME,
        client=db_client
    )
    return fetched_docs


if __name__ == '__main__':
    main()
