"""
Rate the various attributes of a house based on provided criteria.
"""
import json
import pandas as pd
import os
import glob
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


def get_score_for_row(field_name, value, inner_score_dict):
    """Score each row in a listing dataframe.

    The listing is a single-column dataframe where the index is a (category, field)
    MultiIndex and the column is the values for the house.

    The inner_score_dict becomes a simple dictionary in the form:
        {point value: attribute value}, but with a final item of
        {'weight': integer}

    """
    # Make certain field values negative (like prices) for comparison because the lower the better
    reversed_groups = ['price', 'fee']
    if any(x in field_name.lower() for x in reversed_groups):
        try:
            value = -value
        except TypeError:
            pass

    try:
        row_score = inner_score_dict[str(value)]  # exact match (strings, Yes/No, etc.)
    except KeyError:
        row_score = find_closest_key(float(value), inner_score_dict)
    finally:
        weight = inner_score_dict.get('_weight', 1)
        try:
            row_score = row_score * weight
        except TypeError:
            print('\t{0}: {1}'.format(field_name, value))
    return row_score


def find_closest_key(val, dic):
    """Find the closest match to the val in the dict's keys."""
    row_score = 0
    for key, pt_value in dic.items():
        if key == '_weight':
            continue
        elif val > float(key):
            row_score = pt_value
            continue
        else:
            break
    return row_score


def score_house_dict(dic, scorecard):
    """Evaluates a house dictionary against scorecard."""
    house_sc = {'address': dic['info']['full_address'],
                'MLS Number': str(dic['basic_info']['MLS Number'])}
    print(house_sc['address'])
    for k1, v1 in dic.items():
        for field, house_val in v1.items():
            if field in scorecard:
                field_score = get_score_for_row(field, house_val, scorecard[field])
                house_sc[field] = field_score

    # Insert additional special scoring functions here
    score_state(dic, house_sc)
    return house_sc


def write_scorecards_to_file(cards):
    """Dump scorecard(s) into single file."""
    if isinstance(cards, dict):
        cards = [cards]
    json_output_file = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'scorecards.json')
    with open(json_output_file, 'w') as f:
        f.write(json.dumps(cards, indent=4))
    print('Scorecards written to {}'.format(json_output_file))


def score_state(dic, house_sc):
    """Assign a score based on whether it's in VA or MD.
    Eventually, I'll get this down to a city or zip code level with other
    parameters.
    """
    city_state = dic['info']['city_state']
    if 'VA' in city_state.upper():
        state_score = 3.5
    else:
        state_score = 0
    house_sc['state_score'] = state_score


def sum_scores(house_sc):
    total = 0
    item_list = [x for x in house_sc.keys() if x != 'MLS Number']
    for k, v in house_sc.items():
        try:
            total += v
        except TypeError:
            continue
    return total


def main():
    my_scorecard = get_scorecard()

    house_list = []
    house_scorecard_list = []
    for house_file in glob.glob(Code.LISTINGS_GLOB):
        house_dict = json_handling.read_dicts_from_json(house_file)[0]
        house_scorecard = score_house_dict(house_dict, my_scorecard)

        url = house_dict['_metadata']['URL']
        addr = house_dict['info']['full_address']
        total_score = sum_scores(house_scorecard)
        house_list.append((addr, total_score, url))
        house_scorecard_list.append(house_scorecard)
    write_scorecards_to_file(house_scorecard_list)

    # Output as dataframe/CSV
    all_scores = (pd.DataFrame(house_list, columns=['address', 'score', 'URL'])
                  .sort_values('score', ascending=False))
    outfile = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'all_scores.csv')
    all_scores.to_csv(outfile)
    return


def sample():
    my_scorecard = get_scorecard()
    sample_fname = '6551_GRANGE_LN_302.json'
    sample_path = os.path.join(Code.LISTINGS_DIR, sample_fname)
    house = json_handling.read_dicts_from_json(sample_path)[0]

    house_scorecard = score_house_dict(house, my_scorecard)
    house_scorecard['TOTAL_SCORE'] = sum_scores(house_scorecard)

    write_scorecards_to_file(house_scorecard)
    df = pd.DataFrame.from_dict(house_scorecard, orient='index').T
    df.set_index('MLS Number', inplace=True)
    print(df)


if __name__ == '__main__':
    main()
    # sample()
