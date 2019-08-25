
import os
import pandas as pd
import Code
from Code import score2, json_handling


def merge_data_and_scores():
    """Read in data from JSONs and scorecards, then merge as dataframe"""
    sc_path = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'scorecards.json')
    scores = json_handling.read_dicts_from_json(sc_path)
    df_scores = score2.score_dict_list_to_dataframe(scores)

    # Quick dump to file, after rearranging columns
    col_list = list(df_scores.columns)
    col_list.remove('TOTAL_SCORE')
    col_list.insert(1, 'TOTAL_SCORE')
    df_scores = df_scores[col_list]
    raw_scores_path = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'raw_scores.csv')
    df_scores.to_csv(raw_scores_path)

    # Create MultiIndex for scores
    iterables = [['scores'], list(df_scores.columns)]
    mux = pd.MultiIndex.from_product(iterables, names=['first', 'second'])
    df_scores.columns = mux

    df_data = json_handling.all_files_to_dataframe(Code.LISTINGS_GLOB).T

    # Merge on indices
    merged = pd.merge(df_data, df_scores[('scores', 'TOTAL_SCORE')],
                      left_index=True, right_index=True)
    # Drop the top level of the column multiindex (Excel tables don't like it)
    merged = merged.droplevel(level=0, axis=1)
    # Set column headers
    merged = clean_dataframe_columns(merged)
    # Name the index
    merged.index.name = 'MLS Number'

    # Write to file
    outpath = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'master_list.csv')
    merged.to_csv(outpath)


def clean_dataframe_columns(df):
    col_list = [
        'TOTAL_SCORE',
        'URL',
        'full_address',
        'badge',
        'Status',
        'days_on_market',
        'list_price',
        'sale_price',
        'sold',
        'sale_price_diff',
        'sale_diff_pct',
        'sqft',
        'Price Per SQFT',
        'beds',
        'baths',
        'Bathrooms Full',
        'Work commute (Bing)',
        'Work commute (Citymapper)',
        'tether',
        'bus_walk_mins',
        'Year Built',
        'Structure Type',
        'Architectural Style',
        'Unit Building Type',
        'Appliances',
        'Has Basement',
        'Laundry Type',
        'Condo/Coop Fee',
        'HOA Fee',
        'HOA Fee Freq',
        'City/Town Tax',
        'County Tax',
        'Tax Annual Amount',
        'Tax Assessed Value',
        '# of Attached Carport Spaces',
        '# of Attached Garage Spaces',
        '# of Detached Garage Spaces',
        'Assigned Spaces Count',
        'Has Garage',
        'Parking Features',
        'Pool',
        'modify_time',
        'scraped_time',
        'County',
        'city_state',
        'Inclusions',
    ]
    return df[col_list]


if __name__ == '__main__':
    score2.score_all()
    merge_data_and_scores()
