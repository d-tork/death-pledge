"""Run actions on housing search spreadsheet."""

import os
from datetime import datetime
import pandas as pd
import random
from time import sleep
from Code.api_calls import google_sheets, coordinates, citymapper
from Code import scrape, support



def process_data(df):
    df1 = df.copy()
    df1['full_address'] = df1['Address'] + ' ' + df1['Locale']
    df1 = df1.dropna(subset=['Address'])
    df1 = df1.loc[~(df1['Address'] == '')]
    return df1


def get_scraped_data(url_series):
    """Go forth and collect up the MLS data given an array of URLs"""
    # Clean up URLs
    url_series_clean = url_series.apply(lambda x: x[:x.find('?')])
    random.seed(0)
    wait_time = random.random()*10
    click_wait = 3 + random.random()

    browser = scrape.get_browser()
    outer_list = []
    for u in url_series_clean:
        # Check if URL is still valid
        result_code = support.check_status_of_website(u)
        if result_code != 200:
            continue
        inner_dict = scrape.get_full_data_for_url(u, browser, click_wait)
        print('Waiting {} seconds...'.format(wait_time))
        sleep(wait_time)
        if inner_dict:
            outer_list.append(inner_dict)
    browser.quit()
    df = pd.DataFrame(outer_list)
    return df


if __name__ == '__main__':
    dir_path = os.path.dirname(os.path.realpath(__file__))
    start_time = datetime.now()
    print(start_time)

    my_creds = google_sheets.get_creds()
    df_raw = google_sheets.main(my_creds)
    df_mod = process_data(df_raw)

    # Get full df
    df_full = get_scraped_data(df_raw['URL'])
    df_full['full_address'] = df_full['address'] + ' ' + df_full['city']
    print('stop here.')

    print('Getting coordinates from address...')
    df_full['coords'] = df_full['full_address'].apply(coordinates.get_coords)
    print('Done')
    print('Getting commute times from coordinates...')
    df_full['cm_time'] = df_full['coords'].apply(citymapper.get_commute_time)

    DATA_FOLDER = os.path.join(dir_path, '..', 'Data')
    output_file = os.path.join(DATA_FOLDER, 'Processed', 'dffull{}.csv'.format(str(datetime.now())))
    df_full.to_csv(output_file, index=False)
    print('end')
