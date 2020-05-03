#!/Users/dtork/Documents/Python/death-pledge/env37/bin/python
"""Run actions on housing search spreadsheet, in sample mode."""

import os
import logging

import deathpledge
from deathpledge.api_calls import google_sheets as gs
from deathpledge.classes import Home
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
def main():
    google_creds = gs.get_creds()
    df_urls = gs.get_url_dataframe(google_creds, last_n=1)
    house1 = Home(**df_urls.squeeze())  # ONLY works if df_urls is a single row
    #house1 = Home(full_address='1777 WESTWIND WAY MCLEAN, VA 22102')

    # Actions
    house1.scrape(quiet=True, force=True)
    house1.upload(db_name=deathpledge.RAW_DATABASE_NAME)
    house1.clean()
    house1.enrich()
    house1.upload(db_name=deathpledge.DATABASE_NAME)

    gs.refresh_url_sheet(google_creds)


if __name__ == '__main__':
    main()
