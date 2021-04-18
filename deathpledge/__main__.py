"""Run actions on housing search spreadsheet."""
from os import path
import argparse
import logging

import deathpledge
from deathpledge.logs.log_setup import setup_logging
from deathpledge.logs import *
from deathpledge.api_calls import google_sheets as gs, check
from deathpledge import scrape2, support, database, update_sold

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
        update_sold.update_sold(google_creds=google_creds, db_client=cloudant)
        check_new_and_active_from_google(google_creds=google_creds, db_client=cloudant, quiet=True)
        check_and_scrape_homescout(db_client=cloudant, max_pages=args.pages, quiet=True)
        gs.refresh_url_sheet(google_creds, db_client=cloudant)
        update_sold.refresh_sold_list(google_creds=google_creds, db_client=cloudant)
    return


def parse_commandline_arguments():
    parser = argparse.ArgumentParser(
        description="""Run the deathpledge app on URLs in the Google sheet 'House
        decision matrix'. Scrapes, uploads to the raw database, cleans, enriches,
        and then uploads to the clean database.""",
        epilog='Using --force-all overrides --new.'
    )
    parser.add_argument('-n', default=5, type=int, dest='pages',
                        help='Number of pages of results to scrape')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase output verbosity')
    return parser.parse_args()


def check_new_and_active_from_google(google_creds, db_client, **kwargs):
    """Go through google sheet to update actives and scrape new URLs."""
    urls = gs.get_url_dataframe(google_creds)
    to_scrape = urls.loc[urls['next_action'] == 'scrape']
    to_check = urls.loc[urls['next_action'] == 'check'].head(25)
    logger.info(f'{len(to_scrape)} new rows to be scraped')

    if not to_scrape.empty:
        scraped_homes, _ = scrape2.scrape_from_url_df(urls=to_scrape, sign_in=True, **kwargs)
        database.bulk_upload(
            docs=scraped_homes,
            db_name=deathpledge.RAW_DATABASE_NAME,
            client=db_client
        )
        process_and_save(scraped_homes, db_client=db_client)
    if not to_check.empty:
        checked = check.check_urls_for_changes(urls=to_check, sign_in=False)
        database.bulk_upload(checked, db_name=deathpledge.DATABASE_NAME, client=db_client)


def process_and_save(homes: list, db_client: database.Cloudant.iam):
    """Clean and enrich homes, then push to clean.

    Args:
        homes: Scraped listings
        db_client: Cloudant database client for upload

    """
    for home in homes:
        home.clean()
        home.enrich()
        support.update_modified_date(home)
    if homes:
        database.bulk_upload(docs=homes,
                             db_name=deathpledge.DATABASE_NAME,
                             client=db_client)


def check_and_scrape_homescout(db_client, **kwargs):
    scraped_homes = scrape2.scrape_from_homescout_gallery(db_client=db_client, **kwargs)
    if scraped_homes:
        database.bulk_upload(
            docs=scraped_homes, client=db_client, db_name=deathpledge.RAW_DATABASE_NAME
        )
    process_and_save(homes=scraped_homes, db_client=db_client)


if __name__ == '__main__':
    main()
