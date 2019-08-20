import json
import pandas as pd
from datetime import datetime
import os
import glob
import Code
from django.utils.text import slugify

LISTINGS_DIR = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'saved_listings')


def add_dict_to_json(dic):
    """Write listing dict to JSON file. If file already exists, insert the dict.

    :returns list of dicts
        a list of len 1 or more of all scraped versions
    """
    # Define file path
    outname = dic['info']['address']
    outname = slugify(outname).replace('-', '_').upper()
    outfilepath = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'saved_listings',
                               '{}.json'.format(outname))

    all_scrapes = []
    # Read existing dictionaries (if file exists)
    try:
        with open(outfilepath, 'r') as f:
            contents = json.load(f)
            all_scrapes.extend(contents)
    except FileNotFoundError:
        pass

    # Check if newest scrape is different from previous one
    if all_scrapes:
        any_change = check_if_changed(dic, all_scrapes[0])
    else:
        any_change = True

    if any_change:
        # Add modify timestamp
        dic['_metadata'].update({'modify_time': str(datetime.now())})
        # Write new (and old) dictionaries to a list in file
        all_scrapes.insert(0, dic)
        os.makedirs(os.path.dirname(outfilepath), exist_ok=True)
        with open(outfilepath, 'w') as f:
            f.write(json.dumps(all_scrapes, indent=4))
    else:
        print('\tNo change in listing data.')
    return all_scrapes


def check_if_changed(dic1, dic2):
    exclude_category = ['_metadata']
    change_set = set()
    for category in [x for x in dic1.keys() if x not in exclude_category]:
        category_dict = dic1[category]
        for field, value in category_dict.items():
            try:
                if value != dic2[category][field]:
                    change_set.add('Changed: {}'.format(field))
            except KeyError:
                change_set.add('Added: {}'.format(field))
    if change_set:
        dic1['_metadata'].update({'changes': list(change_set)})
        for i in change_set:
            print('\t{}'.format(i))
        return True
    else:
        return False


def dict_to_dataframe(dic):
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


def read_dicts_from_json(filepath):
    """Read JSON dictionaries from a listing file."""
    with open(filepath, 'r') as f:
        listing_all = json.load(f)
    return listing_all


def dict_list_to_dataframe(house_hist):
    """Given a list of JSON dicts, convert them all to a single df."""
    full_df = pd.DataFrame()
    for scrape in house_hist:
        df = dict_to_dataframe(scrape)
        # Rename column header from 'values' to MLS Number
        df.columns = [df.loc[('_metadata', 'modify_time'), 'values']]
        full_df = pd.concat([full_df, df], axis=1)
    return full_df


def all_files_to_dataframe(listings_dir=LISTINGS_DIR):
    full_df = pd.DataFrame()
    listings_path = os.path.join(listings_dir, '*.json')
    for f in glob.glob(listings_path):
        all_entries = read_dicts_from_json(f)
        most_recent = all_entries[0]
        df_indv = dict_to_dataframe(most_recent)
        # Rename column header from 'values' to MLS Number
        df_indv.columns = [df_indv.loc[('basic_info', 'MLS Number'), 'values']]

        full_df = pd.concat([full_df, df_indv], axis=1)
    full_df = full_df.drop('Listing History', level='category')
    return full_df


def sample(listings_dir=LISTINGS_DIR):
    sample_fname = '4304_34TH_ST_S_B2.json'
    sample_fname = '4710_CEDELL_PL.json'
    sample_path = os.path.join(listings_dir, sample_fname)

    all_entries = read_dicts_from_json(sample_path)
    most_recent = all_entries[0]
    df_sample = dict_to_dataframe(most_recent)
    print(df_sample.head())

    df_all = dict_list_to_dataframe(all_entries)
    return most_recent, all_entries


if __name__ == '__main__':
    sample_recent, sample_all = sample(LISTINGS_DIR)
    df1 = dict_list_to_dataframe(sample_all)
    all_listings = all_files_to_dataframe(LISTINGS_DIR)

    df1.to_csv('sample_house_allversions.csv')
    all_listings.to_csv('all_houses.csv')
    print('end here')
