import json
import pandas as pd
import os
import glob
import Code

LISTINGS_DIR = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'saved_listings')


def dict_to_df(dic):
    """Convert listing dictionary to dataframe.
    Derived from SO 24988131
    """
    # Format dictionary and output
    reform = {(outerKey, innerKey): values for outerKey, innerDict in dic.items() for innerKey, values in
              innerDict.items()}

    df = pd.DataFrame.from_dict(reform, orient='index', columns=['values'])
    df.index = pd.MultiIndex.from_tuples(df.index)
    df.index.rename(['category', 'field'], inplace=True)
    return df


def read_list_from_json(filepath):
    """Read JSON dictionaries from a listing file."""
    with open(filepath, 'r') as f:
        listing_all = json.load(f)
    return listing_all


def dict_list_to_df(house_hist):
    """Given a list of JSON dicts, convert them all to a single df."""
    full_df = pd.DataFrame()
    for scrape in house_hist:
        df = dict_to_df(scrape)
        full_df = pd.concat([full_df, df], axis=1)
    return full_df


def sample_main(listings_dir=LISTINGS_DIR):
    sample_fname = '4304_34TH_ST_S_B2.json'
    sample_path = os.path.join(listings_dir, sample_fname)

    all_entries = read_list_from_json(sample_path)
    most_recent = all_entries[0]
    df_sample = dict_to_df(most_recent)
    print(df_sample.head())

    df_all = dict_list_to_df(all_entries)
    return most_recent


def all_files_to_df(listings_dir=LISTINGS_DIR):
    full_df = pd.DataFrame()
    listings_path = os.path.join(listings_dir, '*.json')
    for f in glob.glob(listings_path):
        all_entries = read_list_from_json(f)
        most_recent = all_entries[0]
        df_indv = dict_to_df(most_recent)
        full_df = pd.concat([full_df, df_indv], axis=1)
    return full_df


if __name__ == '__main__':
    #sample_main(listings_dir)
    all_listings = all_files_to_df(LISTINGS_DIR)
    print(all_listings.head())
