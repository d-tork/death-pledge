"""Run actions on housing search spreadsheet."""
from os import path
import argparse
import logging
from datetime import datetime
from time import sleep

import deathpledge
from deathpledge.logs.log_setup import setup_logging
from deathpledge.logs import *
from deathpledge.api_calls import google_sheets as gs, check
from deathpledge import classes, scrape2, support, database

logger = logging.getLogger(__name__)


@support.timing
def main():
    args = parse_commandline_arguments()

    logging_config = path.join(deathpledge.PROJ_PATH, 'config', 'logging.yaml')
    setup_logging(config_path=logging_config, verbose=args.verbose)

    google_creds = gs.GoogleCreds(
        creds_dict=deathpledge.keys.get('Google_creds')
    ).creds

    with database.DatabaseClient() as cloudant:
        if not args.process_only:
            scrape_new_urls_from_google(google_creds=google_creds, db_client=cloudant)
            gs.refresh_url_sheet(google_creds, db_client=cloudant)
            check_and_scrape_homescout(db_client=cloudant, max_pages=args.pages, quiet=False)
            gs.refresh_url_sheet(google_creds, db_client=cloudant)
        process_data(google_creds, db_client=cloudant)
    return


def parse_commandline_arguments():
    parser = argparse.ArgumentParser(
        description="""Run the deathpledge app on URLs in the Google sheet 'House
        decision matrix'. Scrapes, uploads to the raw database, cleans, enriches,
        and then uploads to the clean database.""",
        epilog='Using --force-all overrides --new.'
    )
    parser.add_argument('-n', default=5, type=int, dest='pages',
                        help='Number of pages of results to scrape.')
    parser.add_argument('--process', action='store_true', dest='process_only',
                        help='Only process listings already in the raw db.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase output verbosity')
    return parser.parse_args()


def check_and_scrape_homescout(db_client, **kwargs):
    scrape2.scrape_from_homescout_gallery(db_client=db_client, **kwargs)


def scrape_new_urls_from_google(google_creds, db_client):
    """TODO: still scrape active listings, not just brand new ones.

    However, when they get pushed to raw, they will not have _rev IDs so
    they will be rejected. Need a way to get the _rev for the ones that
    have been updated.

    """
    urls = gs.get_url_dataframe(google_creds)
    urls_no_status = urls.loc[urls['status'].isna()]
    logger.info(f'{len(urls_no_status)} new rows to be scraped')
    urls = temp_shrink_df(urls)
    active_listings, closed_listings = scrape2.scrape_from_url_df(urls=urls)
    if active_listings:
        database.bulk_upload(
            docs=active_listings,
            db_name=deathpledge.RAW_DATABASE_NAME,
            client=db_client
        )
    if closed_listings:
        update_closed_listings(listings=closed_listings, db_client=db_client)


def temp_shrink_df(df):
    """Only keep 60 active rows, no realscout"""
    return df.head(60)


def update_closed_listings(listings, db_client):
    raw_db = db_client[deathpledge.RAW_DATABASE_NAME]
    for home in listings:
        raw_doc = raw_db[home.docid]
        raw_doc['status'] = home['status']
        home['modified_date'] = datetime.now().strftime(deathpledge.TIMEFORMAT)
        raw_doc.save()
        logger.info(f"{home.docid} assumed closed; updated in raw database.")
        sleep(5)


def get_urls_to_scrape(urls):
    """Split off url rows that are either still open or don't exist in database."""
    status_open = urls.df['status'] != 'Closed'
    not_in_db = urls.df['docid'].isna()
    return urls.df.loc[status_open | not_in_db]


def process_data(google_creds, db_client):
    urls = gs.get_url_dataframe(google_creds, last_n=None)
    fetched_raw_docs = database.bulk_fetch_raw_docs(urls, db_client)
    fetched_clean_docs = database.get_active_doc_ids(
        client=db_client, db_name=deathpledge.DATABASE_NAME, est_doc_count=len(fetched_raw_docs))
    clean_docs = []
    for row in urls.itertuples():
        if row.docid in fetched_clean_docs:
            logger.debug(f'doc {row.mls_number} already in clean database')
        try:
            doc = fetched_raw_docs.get(row.docid)
        except (TypeError, KeyError):
            logger.error(f'docid {row.mls_number} not found in clean or raw databases')
            continue
        home = classes.Home(
            url=doc['url'],
            added_date=doc['added_date'],
            docid=doc['mls_number'],
        )
        home.update(doc)
        home.clean()
        home.enrich()
        home['modified_date'] = datetime.now().strftime(deathpledge.TIMEFORMAT)
        try:
            home['_rev'] = fetched_clean_docs[row.docid].get('_rev')
        except KeyError:
            pass
        clean_docs.append(home)
    if clean_docs:
        database.bulk_upload(docs=clean_docs,
                             db_name=deathpledge.DATABASE_NAME,
                             client=db_client)


if __name__ == '__main__':
    main()
