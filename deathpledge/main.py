#!/Users/dtork/Documents/Python/death-pledge/env37/bin/python
"""Run actions on housing search spreadsheet."""

import os
import logging
from sys import argv

import deathpledge
from deathpledge.api_calls import google_sheets as gs
from deathpledge import scrape2, score2, enrich, support, database

logfile = os.path.join(deathpledge.PROJ_PATH, 'Data', 'logfile.log')
logging.basicConfig(
    filename=logfile, filemode='w',
    format='%(levelname)s:%(asctime)s - %(name)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


@support.timing
def main(last_n=None):
    google_creds = gs.get_creds()
    df_urls = gs.get_url_dataframe(google_creds, last_n=last_n, force_all=False)
    house_list = scrape2.scrape_from_url_df(df_urls, quiet=True)
    database.bulk_upload(house_list, 'deathpledge_raw')
    for house in house_list:
        house.clean()
        house.enrich()
    database.bulk_upload(house_list, deathpledge.DATABASE_NAME)


if __name__ == '__main__':
    last = int(argv[1])
    main(last)
