"""Run actions on housing search spreadsheet."""

import os
from datetime import datetime
import pandas as pd
import random
from time import sleep
from Code.api_calls import google_sheets, coordinates, citymapper
from Code import scrape, support


def process_data(df):
    # Trim urls to their base
    df['url'] = df['url'].apply(trim_url)
    # drop rows that I've marked inactive
    return df.loc[df['inactive'] == '']


def trim_url(url_str):
    q_mark = url_str.find('?')
    if q_mark > -1:
        return url_str[:q_mark]
    else:
        return url_str


def get_data_for_url_list(url_series):
    """Go forth and collect up the MLS data given an array of URLs"""
    click_wait = 2 + random.random()

    browser = scrape.get_browser()
    outer_list = []
    for u in url_series:
        random.seed()
        wait_time = random.random()*7
        # Check if URL is still valid
        result_code = support.check_status_of_website(u)
        if result_code != 200:
            continue
        inner_dict = scrape.get_full_data_for_url(u, browser, click_wait)
        if inner_dict:
            print('Waiting {:.1f} seconds...'.format(wait_time))
            sleep(wait_time)
            outer_list.append(inner_dict)
        else:
            print('\tListing not found, moving on.')
    browser.quit()
    df = pd.DataFrame(outer_list)
    return df


def get_coords_and_commute(df):
    """Translate address to geographic coordinates and ping Citymapper for commute time."""
    print('Getting coordinates from address...')
    df['coords'] = df['full_address'].apply(coordinates.get_coords)
    print('Done')
    print('Getting commute times from coordinates...')
    df['cm_time'] = df['coords'].apply(citymapper.get_commute_time)
    return df


if __name__ == '__main__':
    dir_path = os.path.dirname(os.path.realpath(__file__))
    start_time = datetime.now()
    print(start_time)

    my_creds = google_sheets.get_creds()
    df_raw = google_sheets.main(my_creds)
    df_mod = process_data(df_raw)

    # Get full df
    #df_full = get_data_for_url_list(df_mod['url'])
    # TESTING:
    df_full = get_data_for_url_list(df_mod['url'].head(3))

    # Cleaning
    df_full['full_address'] = df_full['address'] + ' ' + df_full['city']
    for col in df_full:
        try:
            df_full[col] = support.parse_numbers_from_string(df_full[col])
        except AttributeError:  # trying to split a float or something
            continue
    print('stop here.')

    # Add commute times
    #df_full = get_coords_and_commute(df_full)

    # Output
    DATA_FOLDER = os.path.join(dir_path, '..', 'Data')
    output_file = os.path.join(DATA_FOLDER, 'Processed', 'dffull{}.csv'.format(str(datetime.now())))
    df_full.T.to_csv(output_file, index=True)
    print('end')
