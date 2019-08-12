import json
import pandas as pd
import numpy as np
import os
import glob
import math
import copy
from Code import json_to_pandas, PROJ_PATH

SCORECARD_PATH = os.path.join(PROJ_PATH, 'Code', 'scores.csv')


def get_scorecard(filepath=SCORECARD_PATH):
    """Create scorecard dictionary from CSV input. Returns a dict."""

    def clean_scorecard_dict(dic):
        """Pop empty criteria-score pairs"""
        dic_copy = copy.deepcopy(dic)  # a shallow copy will modify it mid-loop
        for k1, v1 in dic.items():
            for k2, v2 in v1.items():
                try:
                    if math.isnan(v2):
                        dic_copy[k1].pop(k2)  # remove the dict entry
                except TypeError:  # it's a string
                    continue
        return dic_copy

    scores = pd.read_csv(filepath, index_col=['category', 'field']).sort_index()
    scores = convert_bools(scores)
    scores = convert_dtypes(scores)
    # Coerce column headers to numbers
    scores.columns = [float(x) for x in scores.columns]

    # Convert scores to dict
    d_scores = scores.to_dict(orient='index')
    d_scores = clean_scorecard_dict(d_scores)
    return d_scores


def convert_dtypes(df):
    """Re-acquire datatypes from JSON after converting to dataframe and transposing."""
    for col in df:
        df[col] = pd.to_numeric(df[col], errors='ignore')
    return df


def convert_bools(df):
    """Convert yes/no to bool"""
    return df.replace('Yes', True).replace('No', False)


class FieldNotScored(Exception):
    pass


class FieldNotScraped(Exception):
    pass


def get_score_for_row(index_tuple, value, score_dict):
    try:
        inner_score_dict = score_dict[index_tuple]
    except KeyError:
        raise FieldNotScored('This field not assigned a 1-3 score.')
    row_score = 0
    for score, criteria in inner_score_dict.items():
        if value >= criteria:
            row_score = score
            continue
        else:
            break
    return row_score


def score_state(series, score_dict):
    city_state = series.xs('city_state', level=1).squeeze()
    print('state??: {}'.format(city_state))
    if 'VA' in city_state:
        score_dict['state_score'] = 3.5


def score_a_house(series, score_dict):
    """Evaluate house values against scorecard.

    Returns a dict structured like the house dict
    """
    house_score_dict = {}
    for i, val in series.itertuples():
        # Go row by row in the dataframe
        # Don't forget that right now, df1 is basically a series of only one house
        try:
            row_score1 = get_score_for_row(i, val, score_dict)
            house_score_dict[i] = row_score1
        except FieldNotScored:
            continue
    # Insert additional special scoring functions here
    score_state(series, house_score_dict)
    return house_score_dict


def sum_scores(house_score_dict):
    total = 0
    for v in house_score_dict.values():
        total += v
    return total


def score_multiple_house_files(glob_path, score_dict):
    """Read in a group of files and score each house.

    Returns a list of (house, score) tuples
    """
    house_list = []
    house_scorecard_list = []
    for house_file in glob.glob(glob_path):
        house_dict = json_to_pandas.read_list_from_json(house_file)[0]
        df1 = json_to_pandas.dict_to_df(house_dict)  # What shape is this??
        # shape is probably fields as index, houses as columns
        df1 = convert_bools(df1)
        new_df1_cols = df1.xs('address', level=1).iloc[:, 0]  # drop iloc and squeeze() if it will have more than one row
        df1.columns = new_df1_cols

        house_scorecard = score_a_house(df1, score_dict)

        # Construct lists
        try:
            addr = house_dict['info']['address']
            url = house_dict['_metadata']['URL']
        except KeyError:
            raise FieldNotScraped('Field not in scraped data. Re-run scrape2.py on this listing.')
            continue

        total_score = sum_scores(house_scorecard)
        house_list.append((addr, total_score, url))
        house_scorecard_list.append(house_scorecard)

    # Dump scorecards into single file
    json_output_file = os.path.join(PROJ_PATH, 'Data', 'Processed', 'scorecards.json')
    with open(json_output_file, 'w') as f:
        f.write(json.dumps(house_scorecard_list, indent=4))
    return house_list


if __name__ == '__main__':
    scorecard = get_scorecard()

    # All files
    listings_glob_path = "../Data/Processed/saved_listings/*.json"
    all_houses = score_multiple_house_files(listings_glob_path, scorecard)

    # Output as dataframe/CSV
    all_scores = pd.DataFrame(all_houses, columns=['address', 'score', 'URL'])
    outfile = os.path.join(PROJ_PATH, 'Data', 'Processed', 'all_scores.csv')
    all_scores.to_csv(outfile)
