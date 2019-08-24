"""
Rate the various attributes of a house based on provided criteria.
"""
import json
import pandas as pd
import numpy as np
import os
import glob
import datetime as dt
import Code
from Code import json_handling, modify


def get_scorecard(filepath=Code.SCORECARD_PATH):
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
    house_sc = {'address': dic['_info']['full_address'],
                'MLS Number': str(dic['basic info']['MLS Number'])}
    print(house_sc['address'])
    for k1, v1 in dic.items():
        for field, house_val in v1.items():
            if field in scorecard:
                field_score = get_score_for_row(field, house_val, scorecard[field])
                house_sc[field] = field_score

    # Insert additional special scoring functions here
    score_state(dic, house_sc)
    score_nearest_metro(dic, house_sc)
    all_continuous_scoring(dic, house_sc)
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
    city_state = dic['_info']['city_state']
    if 'VA' in city_state.upper():
        state_score = 3.5
    else:
        state_score = 0
    house_sc['state_score'] = state_score


def score_nearest_metro(dic, house_sc):
    """Evaluate distance to nearest metro"""
    metro = dic['local travel']['Nearby Metro'][0]  # returns a list of [station, (dist, time)]
    dur = dt.datetime.strptime(metro[1][1].split()[0], '%H:%M:%S')
    delta = dt.timedelta(hours=dur.hour, minutes=dur.minute, seconds=dur.second)
    secs = delta.total_seconds()

    # Derived from SO 17118350 and 43095739
    sec_array = np.arange(120, 1, -10) * 60
    score = sec_array.size - np.searchsorted(sec_array[::-1], secs, side='right')
    # Subtract 8 so that the commute times longer than 40 min give it a negative score
    score = float(score) - 6
    # Add weighting (because a close metro is muy importante
    score *= 4
    house_sc['metro_walk_score'] = score


def continuous_score(value, min_value, max_value, weight,
                     ascending=True, norm_by=None, zero_pt=0):
    """Score a value based on a min/max range.

    The scale that determines these scores is arbitrary, and shifts depending on A) the range
    of possible values specified, B) how or if it is normalized, and C) whether or not a zero
    point is set and what it is set to. Therefore the relationship between the scores for
    various values is _relative_, and can be adjusted later by multiplying it by a weighting
    factor.

    My usual weighting scale is between 1 and 3.5 (1 and 3 really, with an extra .5 for values
    that are f***ing outstanding). But if this function returns scores that are all less than
    1, a more appropriate weighting can be applied.

    Finding a good zero point percentage is as easy as
        x = (zerovalue - min) / (max - min)  # for ascending, setting from left
        x = 1 - (zerovalue - min) / (max - min)  # for descending, setting from right

    Args:
        value (num): number to be scored
        min_value (num): bottom of range of potential/expected values in dataset
        max_value (num): top of range of potential/expected values in dataset
        weight (int or float): weighting factor
        ascending (bool): whether to look left-to-right or right-to-left, default True
            Use false when a lower value is scored higher (i.e. price)
        norm_by (int): scale by which to normalize the scores (i.e. 4, 10, 100)
        zero_pt (float): if norm_by, percentage at which to set the zero
            Anything left of the zero point (asc) or right of it (desc) becomes negative and
            detracts from a score, rather than just being a lower score.

    Examples:
        For scoring the listing price, where lower prices are better, and I reasonably
        expect all my prices to be within 275k and 550k:
        >>> import numpy as np
        >>> prices = np.array([350e3, 400e3, 450e3, 500e3])
        >>> continuous_score(prices, 275e3, 550e3, ascending=False, norm_by=10)
        array([7.2, 5.4, 3.6, 1.8])

        Set the zero point at 50% so that the upper half of the price scale becomes
        negative:
        >>>continuous_score(prices, 275e3, 550e3, ascending=False, norm_by=10, zero_pt=.5)
        array([ 2.2,  0.4, -1.4, -3.2])

        An ascending example, as with the number of bedrooms. Zero point set to
        illustrate that 2 beds is expected, more is increasingly better, but 1 is
        unacceptable and should subtract from the overall score so as to disqualify it.
        >>> beds = np.array([1, 2, 3, 4, 5])
        >>> continuous_score(beds, 1, 5, ascending=True, norm_by=4, zero_pt=.2)
        array([-0.8,  0. ,  0.8,  1.6,  2.4])

    Returns:
        int64 or array of int64
            the scores of the value(s) passed

    """
    spread = (max_value - min_value)
    if spread < 50:
        num = spread + 1
    else:
        num = 50
    a = np.linspace(min_value, max_value, num=num)

    if ascending:
        score = np.searchsorted(a, value, side='left')
    else:
        score = np.searchsorted(-a[::-1], -value, side='right')

    # multiply it by (x/50) to normalize on a 0-10 scale (or whatever scale specified)
    if norm_by:
        score = score * (norm_by / num) - (zero_pt * norm_by) * weight
    return score.round(1)


def all_continuous_scoring(dic, house_sc):
    price = dic['_info']['list_price']
    house_sc['price_score'] = continuous_score(
        price, 300e3, 500e3, weight=3, ascending=False, norm_by=4)

    commute_time = dic['quickstats']['commute_transit_mins']
    house_sc['commute_score'] = continuous_score(
        commute_time, 10, 105, weight=3, ascending=False, norm_by=4, zero_pt=.47)

    metro_walk = dic['quickstats']['metro_walk_mins']
    house_sc['metro_walk_score'] = continuous_score(
        metro_walk, 0, 120, weight=3, ascending=False, norm_by=4, zero_pt=.75)

    # Add tax amount
    # Add year built


def sum_scores(house_sc):
    total = 0
    item_list = [x for x in house_sc.keys() if x != 'MLS Number']
    for k in item_list:
        try:
            total += house_sc[k]
        except TypeError:
            continue
    return total


def main():
    my_scorecard = get_scorecard()

    house_list = []  # for simple CSV output
    house_scorecard_list = []  # for JSON output
    for house_file in glob.glob(Code.LISTINGS_GLOB):
        house_dict = json_handling.read_dicts_from_json(house_file)[0]
        house_scorecard = score_house_dict(house_dict, my_scorecard)
        house_scorecard_list.append(house_scorecard)

        total_score = sum_scores(house_scorecard)
        house_scorecard['TOTAL_SCORE'] = total_score

        url = house_dict['_metadata']['URL']
        addr = house_dict['_info']['full_address']
        house_list.append((addr, total_score, url))
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
