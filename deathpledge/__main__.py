"""Run actions on housing search spreadsheet."""
from os import path
import argparse

import deathpledge
from deathpledge.logs.log_setup import setup_logging
from deathpledge.logs import *
from deathpledge.api_calls import google_sheets as gs
from deathpledge import classes, scrape2, support, database


def parse_commandline_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', default=None, type=int, dest='last_n')
    return parser.parse_args()


@support.timing
def main():
    logging_config = path.join(deathpledge.PROJ_PATH, 'config', 'logging.yaml')
    setup_logging(config_path=logging_config)

    # Raw versions
    args = parse_commandline_arguments()
    google_creds = gs.get_creds()
    urls = gs.get_url_dataframe(google_creds, last_n=args.last_n)
    scrape2.scrape_from_url_df(urls, force_all=False, quiet=True)
    gs.refresh_url_sheet(google_creds)

    # Clean versions
    new_urls = gs.get_url_dataframe(google_creds, last_n=args.last_n)
    for row in new_urls.itertuples():
        home = classes.Home(**row._asdict())
        home.fetch(db_name=deathpledge.RAW_DATABASE_NAME)
        home.clean()
        home.enrich()
        home.upload(db_name=deathpledge.DATABASE_NAME)


if __name__ == '__main__':
    main()
