"""Run actions on housing search spreadsheet."""

import os
from datetime import datetime
import pandas as pd
from Code.api_calls import google_sheets, coordinates, citymapper


def process_data(df):
    df1 = df.copy()
    df1['full_address'] = df1['Address'] + ' ' + df1['Locale']
    df1 = df1.dropna(subset=['Address'])
    df1 = df1.loc[~(df1['Address'] == '')]
    return df1


if __name__ == '__main__':
    dir_path = os.path.dirname(os.path.realpath(__file__))
    start_time = datetime.now()
    print(start_time)

    my_creds = google_sheets.get_creds()
    df_raw = google_sheets.main(my_creds)
    df_mod = process_data(df_raw)
    print('Getting coordinates from address...')
    df_mod['coords'] = df_mod['full_address'].apply(coordinates.get_coords)
    print('Done')
    print('Getting commute times from coordinates...')
    df_mod['cm_time'] = df_mod['coords'].apply(citymapper.get_commute_time)

    DATA_FOLDER = os.path.join(dir_path, '..', 'Data')
    output_file = os.path.join(DATA_FOLDER, 'Processed', 'dfmod{}.csv'.format(str(datetime.now())))
    df_mod.to_csv(output_file, index=False)
    print('end')
