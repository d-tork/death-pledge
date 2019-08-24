import json
import pandas as pd
from datetime import datetime
import os
import glob
import Code
from django.utils.text import slugify


def read_dicts_from_json(filepath):
    """Read JSON dictionaries from a house file, as a list of dicts."""
    with open(filepath, 'r') as f:
        listing_all = json.load(f)
    return listing_all


def write_dicts_to_json(dict_list, filepath):
    """Write a version history to a house JSON file.

    A version history is a list of dictionaries.
    Returns nothing.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(json.dumps(dict_list, indent=4))
    print('Listing data written to {}'.format(os.path.basename(filepath)))


def create_filename_from_dict(dic):
    """Generate a JSON filename from address in dict."""
    addr = dic['_info']['address']
    clean_name = slugify(addr).replace('-', '_').upper()
    return '{}.json'.format(clean_name)


def add_dict_to_json(dic):
    """Write listing dict to JSON file. If file already exists, insert the dict.

    :returns list of dicts
        a list of len 1 or more of all scraped versions
    """
    # Define file path
    basename = create_filename_from_dict(dic)
    outfilepath = os.path.join(Code.LISTINGS_DIR, basename)

    all_scrapes = []
    # Read existing dictionaries (if file exists)
    try:
        contents = read_dicts_from_json(outfilepath)
        all_scrapes.extend(contents)
    except FileNotFoundError:
        pass

    # Check if newest scrape is different from previous one
    if all_scrapes:  # previous versions existed
        any_change = check_if_changed(dic, all_scrapes[0])
    else:
        any_change = True

    if any_change:
        # Add modify timestamp
        dic['_metadata'].update({'modify_time': str(datetime.now())})

        # Write new (and old) dictionaries to a list in file
        all_scrapes.insert(0, dic)
        write_dicts_to_json(all_scrapes, outfilepath)
    else:
        # TESTING: Replace the dict anyway because I'm reordering the keys
        all_scrapes.pop(0)
        all_scrapes.insert(0, dic)
        write_dicts_to_json(all_scrapes, outfilepath)
        print('\tNo change in listing data.')
    return all_scrapes


def check_if_changed(dic1, dic2):
    exclude_fields = ['changes', 'modify_time', 'scraped_time']
    change_set = set()
    for category, category_dict in dic1.items():
        for field in [x for x in category_dict if x not in exclude_fields]:
            value = category_dict[field]
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


def remove_dict_from_json(filepath, quantity=None):
    """Pop old versions from JSON file.

    When quantity is none, all old versions are removed and only
    the most recent remains. Otherwise, remove that many versions.

    It will never remove the most recent though. If you want a clean
    start, just delete the file itself.
    """
    all = read_dicts_from_json(filepath)
    keep = [all.pop(0)]
    if quantity is None:
        quantity = len(all)
    del all[-quantity:]  # delete from end number of items in quantity
    print('Removed {} old versions from {}'.format(quantity, os.path.basename(filepath)))
    # Write the kept version back out to JSON
    write_dicts_to_json(keep, filepath)


def clear_all_json_histories(fileglob):
    for f in glob.glob(fileglob):
        remove_dict_from_json(f)


def check_and_merge_dicts(dic1):
    """Add fields which are missing in a dictionary.

    When scraping from a URL, but a JSON already exists for that house
    with external data, merge the two after the fresh scraping so I don't
    have to re-run modify.py to add in commute times, distances, etc.

    :arg
        dic1 (dict): shorter, newly-scraped dict

    :returns None; modifies dic1 in place, or not at all
    """
    # Look for an existing file with a dict in it
    basename = create_filename_from_dict(dic1)
    filepath = os.path.join(Code.LISTINGS_DIR, basename)
    try:
        dic2 = read_dicts_from_json(filepath)[0]
    except FileNotFoundError:
        return

    # If file was found, proceed with comparison to dic2
    for category, category_dict in dic2.items():
        dic1[category] = dic1.get(category, category_dict)
        for field, value in category_dict.items():
            dic1[category][field] = dic1[category].get(field, value)
    print('\tAdditional categories carried over from previous version.')


def dict_to_dataframe(dic):
    """Convert listing dictionary to dataframe.
    Derived from SO 24988131
    """
    # Format dictionary and output
    reform = {(outerKey, innerKey): values for outerKey, innerDict in dic.items() for innerKey, values in
              innerDict.items()}

    # Convert to dataframe, then MultiIndex from the tuple keys
    df = pd.DataFrame.from_dict(reform, orient='index', columns=['values'])
    df.index = pd.MultiIndex.from_tuples(df.index)
    df.index.rename(['category', 'field'], inplace=True)
    # Rename the columns to MLS numbers
    df.columns = [df.loc[('basic info', 'MLS Number'), 'values']]
    return df


def dict_list_to_dataframe(house_hist):
    """Given a list of JSON dicts, convert them all to a single df."""
    full_df = pd.DataFrame()
    for scrape in house_hist:
        df = dict_to_dataframe(scrape)
        full_df = pd.concat([full_df, df], axis=1)
    # Rename column headers from their MLS number to their order in the file
    new_col_headers = list(reversed(range(len(full_df.columns))))
    full_df.columns = new_col_headers
    return full_df


def all_files_to_dataframe(listings_glob):
    full_df = pd.DataFrame()
    for f in glob.glob(listings_glob):
        all_entries = read_dicts_from_json(f)
        most_recent = all_entries[0]
        df_indv = dict_to_dataframe(most_recent)
        full_df = pd.concat([full_df, df_indv], axis=1)
    # Drop listing history rows, because they don't line up for all houses and are unwieldy
    full_df = full_df.drop('Listing History', level='category')
    return full_df


def sample(listings_dir):
    sample_fname = '6551_GRANGE_LN_302.json'
    sample_path = os.path.join(listings_dir, sample_fname)

    all_entries = read_dicts_from_json(sample_path)
    most_recent = all_entries[0]
    df_sample = dict_to_dataframe(most_recent)
    print(df_sample.head())

    df_all = dict_list_to_dataframe(all_entries)

    all_listings = all_files_to_dataframe(Code.LISTINGS_DIR)

    df_all.to_csv('sample_house_allversions.csv')
    all_listings.to_csv('all_houses.csv')
    return


if __name__ == '__main__':
    # sample(Code.LISTINGS_DIR)
    # clear_all_json_histories(Code.LISTINGS_GLOB)
    single_path = os.path.join(Code.LISTINGS_DIR, '4304_34TH_ST_S_B2.json')
    remove_dict_from_json(single_path)

    # df1 = all_files_to_dataframe(Code.LISTINGS_GLOB).T
    # df1.to_csv(os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'all_listings.csv'))
