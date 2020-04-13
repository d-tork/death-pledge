"""Run actions on housing search spreadsheet."""

import os
import logging

import Code
from Code.api_calls import google_sheets as gs
from Code import scrape2, score2, modify, support, database

logfile = os.path.join(Code.PROJ_PATH, 'Data', 'logfile.log')
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
    df_urls = gs.get_url_dataframe(google_creds, last_n=None, force_all=True)
    house_list = scrape2.scrape_from_url_df(df_urls, quiet=True)
    database.bulk_upload(house_list, 'deathpledge_raw')
    for house in house_list:
        house.clean()
    database.bulk_upload(house_list, 'deathpledge_clean')
    #modify.modify_all()
    #score2.score_all()


@support.timing
def single_sample():
    #house1 = Code.classes.Home(url='https://daniellebiegner.realscout.com/homesearch/listings/p-5825-piedmont-dr-alexandria-22310-brightmls-33')
    house1 = Code.classes.Home(url='https://daniellebiegner.realscout.com/homesearch/listings/p-1724-kingsgate-ct-304-alexandria-22302-brightmls-346')
    house1.scrape(quiet=True)
    house1.clean()
    house1.upload(db_name='deathpledge_clean')

    """
    modify.modify_one(house1)
    my_sc = score2.get_scorecard()
    sample_sc = score2.score_single(house1, my_sc)
    score2.write_scorecards_to_file(sample_sc)
    """


if __name__ == '__main__':
    main()
    #single_sample()
