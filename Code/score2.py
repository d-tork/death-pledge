"""
Rate the various attributes of a house based on provided criteria.

Any field added to the house's scorecard dict should be in the form
    'field_name_score'
where all spaces are replaced with underscores and the whole name
is lowercase. This aids with dataframe creation later.
"""
import json
import pandas as pd
import numpy as np
import os
import glob
import datetime as dt
import Code
from Code import json_handling


def get_scorecard(filepath=Code.SCORECARD_PATH):
    """Create scorecard dictionary from JSON file."""
    with open(filepath, 'r') as f:
        scores = json.loads(f.read())
    return scores


class FieldNotScored(Exception):
    pass


def get_score_for_item(field_name, value, inner_score_dict):
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
        try:
            row_score = find_closest_key(float(value), inner_score_dict)
        except ValueError:  # not an exact match, but still a string
            row_score = 0
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
                field_score = get_score_for_item(field, house_val, scorecard[field])
                new_fieldname = '{}_score'.format(field.lower().replace(' ', '_'))
                house_sc[new_fieldname] = field_score

    # Insert additional special scoring functions here
    score_nearest_metro(dic, house_sc)
    all_continuous_scoring(dic, house_sc)
    return house_sc


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
    factor and/or changing the normalization.

    If an attribute's scores are not influencing the total score in the way you'd like it to,
    first normalize it by increasing norm_by. Traditionally, I scored attributes on a 0-3.5
    scale, and when the total score was calculated they were multiplied by their weight
    factor. But now, for the ultra-important attributes, I can score them on different scales
    like 1-10 or 1-15, _then_ multiplied by their weight.

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
        norm_by (float): scale by which to normalize the scores (i.e. 4, 10, 100)
        zero_pt (float): if norm_by, percentage at which to set the zero
            Anything left of the zero point (asc) or right of it (desc) becomes negative and
            detracts from a score, rather than just being a lower score.

    Examples:
        For scoring the listing price, where lower prices are better, and I reasonably
        expect all my prices to be within 275k and 550k:
        >>> import numpy as np
        >>> prices = np.array([350e3, 400e3, 450e3, 500e3])
        >>> continuous_score(prices, 275e3, 550e3, weight=3, ascending=False, norm_by=10)
        array([7.2, 5.4, 3.6, 1.8])

        Set the zero point at 50% so that the upper half of the price scale becomes
        negative:
        >>> continuous_score(prices, 275e3, 550e3, weight=3, ascending=False, norm_by=10, zero_pt=.5)
        array([ -7.8,  -9.6, -11.4, -13.2])

        An ascending example, as with the number of bedrooms. Zero point set to
        illustrate that 2 beds is expected, more is increasingly better, but 1 is
        unacceptable and should subtract from the overall score so as to disqualify it.
        >>> beds = np.array([1, 2, 3, 4, 5])
        >>> continuous_score(beds, 1, 5, weight=1, ascending=True, norm_by=4, zero_pt=.2)
        array([-0.8,  0. ,  0.8,  1.6,  2.4])

    Returns:
        int64 or array of int64
            the scores of the value(s) passed

    """
    if value is None:
        raise ValueError('\tNo value passed to scoring function.')

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
        score = (score * (norm_by / num) - (zero_pt * norm_by)) * weight
    return score.round(1)


def all_continuous_scoring(dic, house_sc):
    """Stores and runs continuous scoring functions for each attribute.

    Uses dict.get() to avoid KeyErrors if the field is not in the house dict.
    If it's not, prints the error and moves on without scoring it.
    """
    price = dic['_info'].get('list_price')
    try:
        house_sc['price_score'] = continuous_score(
            price, 275e3, 525e3, weight=2.5, ascending=False, norm_by=3.5)
    except ValueError as e:
        print(e)

    commute_time = dic['quickstats'].get('commute_transit_mins')
    try:
        house_sc['commute_score'] = continuous_score(
            commute_time, 15, 120, weight=8, ascending=False, norm_by=4, zero_pt=.47)
    except ValueError as e:
        print(e)

    metro_walk = dic['quickstats'].get('metro_walk_mins')
    try:
        house_sc['metro_walk_score'] = continuous_score(
            metro_walk, 0, 120, weight=4, ascending=False, norm_by=4, zero_pt=.65)
    except ValueError as e:
        print(e)

    tax_amt = dic['expenses / taxes'].get('Tax Annual Amount')
    if (tax_amt == 0) | (tax_amt is None):
        pass
    else:
        house_sc['tax_amount_score'] = continuous_score(
            tax_amt, 100, 6500, weight=1, ascending=False, norm_by=3.5)

    year = dic['basic info'].get('Year Built')
    try:
        house_sc['year_score'] = continuous_score(
            year, 1900, 2020, weight=2, ascending=True, norm_by=3.5, zero_pt=.42)
    except ValueError as e:
        print(e)

    sqft = dic['_info'].get('sqft')
    try:
        house_sc['sqft_score'] = continuous_score(
            sqft, 900, 2000, weight=1, ascending=True, norm_by=3.5)
    except ValueError as e:
        print(e)

    price_sqft = dic['basic info'].get('Price Per SQFT')
    try:
        house_sc['price_SQFT_score'] = continuous_score(
            price_sqft, 110, 376, weight=3, ascending=False, norm_by=3.5)
    except ValueError as e:
        print(e)

    tether = dic['quickstats'].get('tether')
    try:
        house_sc['tether_score'] = continuous_score(
            tether, 0, 10.5, weight=2, ascending=False, norm_by=3.5, zero_pt=0.24)
    except ValueError as e:
        print(e)

    buswalk = dic['quickstats'].get('bus_walk_mins')
    try:
        house_sc['bus_walk_score'] = continuous_score(
            buswalk, 0, 30, weight=4, ascending=False, norm_by=4, zero_pt=0.75)
    except ValueError as e:
        print(e)


def sum_scores(house_sc):
    """Sum up all scores in the scorecard and write to scorecard."""
    total = 0
    item_list = [x for x in house_sc.keys() if x != 'MLS Number']
    for k in item_list:
        try:
            total += house_sc[k]
        except TypeError:
            continue
    house_sc['TOTAL_SCORE'] = round(total, 1)


def write_scorecards_to_file(cards):
    """Dump scorecard(s) into single file."""
    if isinstance(cards, dict):
        cards = [cards]
    json_output_file = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'scorecards.json')
    with open(json_output_file, 'w') as f:
        f.write(json.dumps(cards, indent=4))
    print('Scorecards written to {}'.format(json_output_file))


def score_dict_list_to_dataframe(sc_list):
    """Given a list of JSON dicts, convert them all to a single df."""
    full_df = pd.DataFrame()
    for sc in sc_list:
        df = pd.DataFrame.from_dict(sc, orient='index').T.set_index('MLS Number')
        full_df = pd.concat([full_df, df], axis=0, sort=False)
    # Rename column headers from their MLS number to their order in the file
    return full_df


def score_single(house, scorecard):
    """Score a single house"""
    house_sc = score_house_dict(house, scorecard)
    sum_scores(house_sc)
    return house_sc


def score_all():
    my_scorecard = get_scorecard()

    house_sc_list = []  # for JSON output
    for house_file in glob.glob(Code.LISTINGS_GLOB):
        house_dict = json_handling.read_dicts_from_json(house_file)[0]
        house_sc = score_single(house_dict, my_scorecard)
        house_sc_list.append(house_sc)

    write_scorecards_to_file(house_sc_list)
    return


def sample():
    my_scorecard = get_scorecard()
    sample_fname = '4304_34TH_ST_S_B2.json'
    sample_path = os.path.join(Code.LISTINGS_DIR, sample_fname)
    sample_house = json_handling.read_dicts_from_json(sample_path)[0]

    sample_house_sc = score_single(sample_house, my_scorecard)

    write_scorecards_to_file(sample_house_sc)
    sample_df = score_dict_list_to_dataframe([sample_house_sc])
    print(sample_df.T)


if __name__ == '__main__':
    score_all()
    # sample()
