"""Run actions on housing search spreadsheet."""
from os import path
import argparse

import deathpledge
from deathpledge.logs.log_setup import setup_logging
from deathpledge.logs import *
from deathpledge.api_calls import google_sheets as gs
from deathpledge import scrape2, support, database


def parse_commandline_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', default=None, type=int, dest='last_n')
    return parser.parse_args()


@support.timing
def main():
    logging_config = path.join(deathpledge.PROJ_PATH, 'config', 'logging.yaml')
    setup_logging(config_path=logging_config)

    google_creds = gs.get_creds()
    args = parse_commandline_arguments()
    urls = gs.get_url_dataframe(google_creds, last_n=args.last_n)
    house_list = scrape2.scrape_from_url_df(urls, force_all=False, quiet=True)
    database.bulk_upload(house_list, deathpledge.RAW_DATABASE_NAME)
    for house in house_list:
        house.clean()
        house.enrich()
    database.bulk_upload(house_list, deathpledge.DATABASE_NAME)
    gs.refresh_url_sheet(google_creds)


if __name__ == '__main__':
    main()
