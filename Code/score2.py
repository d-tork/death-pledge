"""
Rate the various attributes of a house based on provided criteria.
"""
import json
import pandas as pd
import os
import glob
import math
import copy
import Code
from Code import json_handling

SCORECARD_PATH = os.path.join(Code.PROJ_PATH, 'Data', 'scorecard.json')


def get_scorecard(filepath=SCORECARD_PATH):
    """Create scorecard dictionary from JSON file."""
    with open(filepath, 'r') as f:
        scores = json.loads(f.read())
    return scores


def convert_bools(df):
    """Convert yes/no to bool"""
    return df.replace('Yes', True).replace('No', False)


class FieldNotScored(Exception):
    pass


def get_score_for_row(index_tuple, value, score_dict):
    """Score each row in a listing dataframe.

    The listing is a single-column dataframe where the index is a (category, field)
    MultiIndex and the column is the values for the house.

    The inner_score_dict becomes a simple dictionary in the form:
        {point value: attribute value}, but with a final item of
        {'weight': integer}

    """
    field_name = index_tuple[1]
    try:
        inner_score_dict = score_dict[field_name]
    except KeyError:
        raise FieldNotScored('This field not assigned a 1-3 score.')

    try:
        row_score = inner_score_dict[str(value)]  # exact match
    except KeyError:
        row_score = find_closest_key(str(value), inner_score_dict)
    finally:
        weight = inner_score_dict.get('weight', 1)
        row_score = row_score * weight
    return row_score


def find_closest_key(val, dic):
    """Find the closest match to the val in the dict's keys.

    So far, I believe that 'Yes' will always be greater than 'No', so I don't
    need to convert them to bools or ints. However, if I come up with any ordered
    criteria that's not an exact match, this may not turn out correctly.
    """
    row_score = 0
    for key, pt_value in dic.items():
        if key == '_weight':
            continue
        elif val > key:
            row_score = pt_value
            continue
        else:
            return row_score


def score_a_house(df, scorecard):
    """Evaluate house values against scorecard.

    Returns a dict structured like the house dict
    """
    house_score_dict = {'address': df.xs('address', level=1).squeeze()}
    for i, val in df.itertuples():
        # Go row by row in the dataframe
        # Don't forget that right now, df1 is basically a series of only one house
        _, k2 = i  # Discard first level of dict (category) for scorecards
        try:
            row_score = get_score_for_row(i, val, scorecard)
            house_score_dict[k2] = row_score
        except FieldNotScored:
            continue
    # Insert additional special scoring functions here
    score_state(df, house_score_dict)
    return house_score_dict


def score_multiple_house_files(glob_path, scorecard):
    """Read in a group of files and score each house.

    Returns a list of (house, score) tuples
    """
    house_list = []
    house_scorecard_list = []
    for house_file in glob.glob(glob_path):
        house_dict = json_handling.read_dicts_from_json(house_file)[0]
        df1 = json_handling.dict_to_dataframe(house_dict)
        # shape is (category, field) as MultiIndex, house as column
        new_df1_cols = df1.xs('MLS Number', level=1).iloc[:, 0]
        df1.columns = new_df1_cols

        house_scorecard = score_a_house(df1, scorecard)

        # Construct lists
        try:
            addr = ', '.join([house_dict['info']['address'], house_dict['info']['city_state']])
            url = house_dict['_metadata']['URL']
        except KeyError:
            print('\tField not in scraped data. Re-run scrape2.py on this listing.')
            continue

        print(addr)
        total_score = sum_scores(house_scorecard)
        house_list.append((addr, total_score, url))
        house_scorecard_list.append(house_scorecard)

    # Dump scorecards into single file
    json_output_file = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'scorecards.json')
    with open(json_output_file, 'w') as f:
        f.write(json.dumps(house_scorecard_list, indent=4))
    return house_list


def score_state(series, score_dict):
    city_state = series.xs('city_state', level=1).squeeze()
    if 'VA' in city_state:
        state_score = 3.5
    else:
        state_score = 0
    score_dict.update({'state_score': state_score})


def sum_scores(house_score_dict):
    total = 0
    for k, v in house_score_dict.items():
        try:
            total += v
        except TypeError:
            continue
    return total


def main():
    my_scorecard = get_scorecard()

    # All files
    all_houses = score_multiple_house_files(Code.LISTINGS_GLOB, my_scorecard)

    # Output as dataframe/CSV
    all_scores = (pd.DataFrame(all_houses, columns=['address', 'score', 'URL'])
                  .sort_values('score', ascending=False))
    outfile = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'all_scores.csv')
    all_scores.to_csv(outfile)


def sample():
    my_scorecard = get_scorecard()


if __name__ == '__main__':
    main()
