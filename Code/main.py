"""Run actions on housing search spreadsheet."""

import os
from datetime import datetime
import pandas as pd


def import_from_google(year, sheet_dict=GOOGLE_SHEET_DICT):

    my_creds = quickstart.get_creds()

    print('\n', year)
    year_dict = sheet_dict[year]
    results = quickstart.main(my_creds, year_dict)

    # Turn Google query results from list into dataframe
    df_full = pd.DataFrame()
    for month_sheet, data in results.items():
        df = pd.DataFrame.from_records(data=results[month_sheet])
        df_full = df_full.append(df, ignore_index=True, sort=False)
    df_full.columns = year_dict['col_headers']

    print(df_full.describe())
    print(df_full.head(5))
    print(df_full.tail(5))
    return df_full


if __name__ == '__main__':
    start_time = datetime.now()
    print(start_time)

    SRC_DATA_FOLDER = os.path.join('..', 'Data', 'Raw')
    SRC_DATA_FILE = ''