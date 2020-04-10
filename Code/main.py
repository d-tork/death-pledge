#!/Users/dtork/.local/share/virtualenvs/death-pledge-ki0k_bpH/bin/python
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
    df_urls = gs.get_url_dataframe(google_creds, last_n=28, force_all=False)
    house_list = scrape2.scrape_from_url_df(df_urls, quiet=True)
    database.bulk_upload(house_list, 'deathpledge_raw')
    for house in house_list:
        house.clean()
    database.bulk_upload(house_list, 'deathpledge_clean')
    #modify.modify_all()
    #score2.score_all()


def single_sample():
    df_urls = gs.get_url_dataframe(gs.get_creds(), last_n=1)
    house_list = scrape2.scrape_from_url_df(df_urls, quiet=True)
    house1 = house_list[0]
    house1.clean()
    house1.upload(db_name='deathpledge_test')

    """
    modify.modify_one(house1)
    my_sc = score2.get_scorecard()
    sample_sc = score2.score_single(house1, my_sc)
    score2.write_scorecards_to_file(sample_sc)
    """


if __name__ == '__main__':
    main()
    #single_sample()
