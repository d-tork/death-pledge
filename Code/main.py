#!/Users/dtork/.local/share/virtualenvs/death-pledge-ki0k_bpH/bin/python
"""Run actions on housing search spreadsheet."""

import os

import Code
from Code.api_calls import google_sheets as gs, keys
from Code import scrape2, score2, modify, json_handling, pandas_handling, support

# Scrape all URLs from google
# Re-scrape all on-market JSONS
# Supplement all
# Score all
# Pull from Google
# Push all to Google


@support.timing
def main():
    google_creds = gs.get_creds()
    df_urls = gs.get_url_list(google_creds, last_n=5, force_all=False)
    scrape2.scrape_from_url_df(df_urls, quiet=True)
    modify.modify_all()
    score2.score_all()


def single_sample():
    sample_url_list = [keys.sample_url3]
    temp_glob = os.path.join(Code.LISTINGS_DIR, '6551_GRANGE_LN_302.json')
    # json_handling.clear_all_json_histories(temp_glob)
    # scrape2.scrape_from_url_df(sample_url_list)
    sample_house = json_handling.read_dicts_from_json(temp_glob)[0]
    modify.modify_one(sample_house)
    my_sc = score2.get_scorecard()
    sample_sc = score2.score_single(sample_house, my_sc)
    score2.write_scorecards_to_file(sample_sc)


if __name__ == '__main__':
    main()
    # single_sample()
