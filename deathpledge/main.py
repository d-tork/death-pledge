"""Run actions on housing search spreadsheet."""

import os
import logging
import argparse

import deathpledge
from deathpledge.api_calls import google_sheets as gs
from deathpledge import scrape2, support, database

logfile = os.path.join(deathpledge.PROJ_PATH, 'Data', 'logfile.log')
logging.basicConfig(
    filename=logfile, filemode='w',
    format='%(levelname)s:%(asctime)s - %(name)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def parse_commandline_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--number', default=None, type=int, dest='last_n')
    return parser.parse_args()


@support.timing
def main():
    google_creds = gs.get_creds()
    args = parse_commandline_arguments()
    urls = gs.get_url_dataframe(google_creds, last_n=args.last_n)
    house_list = scrape2.scrape_from_url_df(urls, force_all=False, quiet=True)
    # TODO: split off listing card here
    database.bulk_upload(house_list, deathpledge.RAW_DATABASE_NAME)
    for house in house_list:
        house.clean()
        house.enrich()
    database.bulk_upload(house_list, deathpledge.DATABASE_NAME)
    gs.refresh_url_sheet(google_creds)


if __name__ == '__main__':
    main()
