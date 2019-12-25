
import os
import pandas as pd
import Code
from Code import score2, json_handling


def merge_data_and_scores():
    """Read in data from JSONs and scorecards, then merge as dataframe. """
    sc_path = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'scorecards.json')
    scores = json_handling.read_dicts_from_json(sc_path)
    df_scores = score2.score_dict_list_to_dataframe(scores)

    # Quick dump to file, after rearranging columns
    col_list = list(df_scores.columns)
    col_list.remove('TOTAL_SCORE')
    col_list.insert(1, 'TOTAL_SCORE')
    df_scores = df_scores[col_list].sort_values('TOTAL_SCORE', ascending=False)
    raw_scores_path = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'raw_scores.csv')
    df_scores.to_csv(raw_scores_path)

    # Create MultiIndex for scores
    iterables = [['scores'], list(df_scores.columns)]
    mux = pd.MultiIndex.from_product(iterables, names=['first', 'second'])
    df_scores.columns = mux

    df_data = json_handling.all_files_to_dataframe(Code.LISTINGS_GLOB).T

    # Merge on indices
    merged = pd.merge(df_data, df_scores, how='left',
                      left_index=True, right_index=True)
    # Drop the top level of the column multiindex (Excel tables don't like it)
    merged = merged.droplevel(level=0, axis=1)
    df_scores = df_scores.droplevel(level=0, axis=1)
    # Drop the index (MLS Number already exists as a field)
    merged.reset_index(drop=True, inplace=True)
    # Remove duplicate columns (coming from both data and scorecards)
    merged = merged.loc[:, ~merged.columns.duplicated()]
    # Sort by total score
    merged.sort_values('TOTAL_SCORE', ascending=False, inplace=True)

    # Append to master file
    outpath = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'master_list.csv')
    append_to_master(merged, outpath)
    return merged, df_scores


def append_to_master(df, master_fp):
    """Append most recent data to master csv, removing duplicates."""
    # Read in master
    master = pd.read_csv(master_fp, index_col=0)
    # Append new data
    master = pd.concat([master, df], axis=0, ignore_index=True, sort=False)
    # Sort by last modified
    master.sort_values('modify_time', inplace=True)
    # Drop duplicates with same modify_time
    dupe_fields = ['MLS Number', 'modify_time']
    master.drop_duplicates(subset=dupe_fields, inplace=True)
    exclude_fields = ['scraped_time', 'percentile', 'changes']  # another way of subsetting
    # Write back out
    master.to_csv(master_fp, index_label='index')


def master_list_columns(df):
    col_list = [
        'TOTAL_SCORE',
        'URL',
        'full_address',
        'date_added',
        'badge',
        'Status',
        'days_on_market',
        'list_price',
        'change',
        'pct_change',
        'sqft',
        'Price Per SQFT',
        'beds',
        'baths',
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
        'tax_assessed_diff',
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
        'sold',
        'sale_price',
        'sale_price_diff',
        'sale_diff_pct'
    ]
    return df[col_list]


if __name__ == '__main__':
    score2.score_all()
    merge_data_and_scores()
