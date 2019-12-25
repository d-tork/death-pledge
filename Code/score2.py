"""Rate the various attributes of a house based on provided criteria.

Dynamically reads two different types of scorecards from a single JSON file
and applies those scores and weights to the attributes in a house JSON file.

The first type of scorecard contains attributes whose possible values are
known and enumerated, i.e. a house can be only one of several specific structure
types, and each structure type is worth a certain number of points, and the
whole field of "Structure Type" is weighted according to how much it matters
in calculating the total score.

The second type of scorecard contains attributes whose possible values cannot
be enumerated because they can fall anywhere within a range of values, i.e.
price or distance. For these, a min and max are set which determine at what value
that attribute would receive 0 points, and at what value it would receive the
maximum number of points.

Any new field added to the house's scorecard dict should be in the form:
    `'<field_name>_score'`
where all spaces are replaced with underscores, the whole name is lowercase, and
it ends with '_score'. This aids with dataframe creation later.

Contents:
    - get_scorecard():                    Gets the scorecard from file.
    - get_score_for_item():               Scores an attribute.
    - find_closest_key():                 Gets closest score (deprecated).
    - score_house_dict():                 Score a whole house.
    - score_nearest_metro():              Score the nearest metro walk (deprecated).
    - continuous_score():                 Score attributes over a range.
    - all_continuous_scoring():           Use :func:`continuous_score` with args from a file.
    - score_laundry():                    Score the existence of laundry machines.
    - sum_scores():                       Sum all scores in a dictionary.
    - write_scorecards_to_file():         Output scorecard(s) to a scorecards.json
    - score_dict_list_to_dataframe():     Convert scorecards to a dataframe.
    - write_score_percentiles_to_jsons(): Write to house file total score and kth percentile.
    - score_all():                        Score all houses in folder.
    - sample():                           Score a single specified house (testing).

"""
import json
import os
import glob
import pandas as pd
import numpy as np
from scipy import stats

import Code
from Code import json_handling, modify


def get_scorecard(filepath=None, mode='regular'):
    """Create scorecard dictionary from JSON file.

    Args:
        filepath (str, optional): Where to find ``scorecard.json``. Defaults to ``None``.
            Optional because the default scorecard path is saved as a package-level variable.
        mode (str, optional):  Which dict to get from the scorecard. Defaults to 'regular'.
            Must be either 'regular' or 'continuous'.

    Returns:
        dict: A scorecard.

    Raises:
        ValueError: If an invalid argument is passed to *mode*.

    """
    if filepath is None:
        filepath = Code.SCORECARD_PATH

    if mode == 'regular':
        index = 0
    elif mode == 'continuous':
        index = 1
    else:
        raise ValueError("mode must be 'regular' or 'continuous'")

    with open(filepath, 'r') as f:
        scores = json.loads(f.read())[index]
    return scores


class FieldNotScored(Exception):
    pass


def get_score_for_item(inner_score_dict, field_name, value):
    """Score each value in a house listing if that field exists in the scorecard.

    Args:
        inner_score_dict (dict): Potential field values and their corresponding scores.
            In the form ``{field value: points}``, but with a final item of
            ``{'_weight': <float>}``.
        field_name (str): Name of house attribute currently being scored.
        value (str or float): Value of the house attribute currently being scored.

    Returns:
        float: The attribute's score determined by the attribute value for the house.

    Raises:
        TypeError: If the score dict gives back a string instead of a number for *row_score*.

    """
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
            error_msg = '\tfailed to score {2} for ({0}: {1})'.format(row_score, field_name, value)
            raise TypeError(error_msg)
    return row_score


def find_closest_key(val, dic):
    """Find the closest match to the val in the dict's keys.

    Largely deprecated in favor of using :func:`continuous_score`.
    Acts like a LOOKUP in Excel.

    Args:
        val (float): Value of the house attribute currently being scored.
        dic (dict): Potential field values and their corresponding scores.
            The "inner score dict" corresponding to the house attribute field.

    Returns:
        Closest matching score in the inner score dict.

    """
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


def score_house_dict(dic, scorecard, cont_scorecard):
    """Evaluates a house listing against scorecard.

    Args:
        dic (dict): House listing.
        scorecard (dict): From full scorecard, standard attributes.
        cont_scorecard (dict): From full scorecard, continuous attributes.

    Returns:
        dict: Scorecard for individual house listing.

    """
    house_sc = {'address': dic['_info']['full_address'],
                'MLS Number': str(dic['basic info']['MLS Number']),
                'badge': dic['_info']['badge']
                }
    print(house_sc['address'])
    for k1, v1 in dic.items():
        for field, house_val in v1.items():
            if field in scorecard:
                field_score = get_score_for_item(scorecard[field], field, house_val)
                new_fieldname = '{}_score'.format(field.lower().replace(' ', '_'))
                house_sc[new_fieldname] = field_score

    # Insert additional special scoring functions here
    all_continuous_scoring(dic, house_sc, cont_scorecard)
    score_laundry(dic, house_sc)

    # Sum up scores
    sum_scores(house_sc)
    return house_sc


def continuous_score(value, min_value, max_value, weight,
                     ascending=True, norm_by=3.5, zero_pt=0, **kwargs):
    """Score a value based on a min/max range.

    The scale that determines these scores is arbitrary, and shifts depending on:
        A) the range of possible values specified,
        B) how or if it is normalized, and
        C) whether or not a zero point is set and what it is set to.
    Therefore the relationship between the scores for various values is **relative**, and can
    be adjusted later by multiplying it by a weighting factor and/or changing the normalization.

    If an attribute's scores are not influencing the total score in the way you'd like it to,
    first normalize it by increasing *norm_by*. Traditionally, I scored attributes on a 0-3.5
    scale, and when the total score was calculated they were multiplied by their weight
    factor (typically between 1 and 4). But now, for the ultra-important attributes, I can 
    score them on different scales like 1-10 or 1-15, **then** multiply them by a weight.

    Args:
        value (num): Number to be scored.
        min_value (num): Bottom of range of potential/expected values in dataset.
        max_value (num): Top of range of potential/expected values in dataset.
        weight (int or float): Weighting factor.
        ascending (bool, optional): Whether to look left-to-right or right-to-left.
            Defaults to ``True``.

            Use ``False`` when a lower value is scored higher (i.e. price).
        norm_by (float, optional): Max value of scale by which to normalize the scores.
            Defaults to 3.5.

            Pretty much every attribute is normalized on a 0 to 3.5 scale. Very important
            attributes are 0 to 4 for that extra umph. Extremely important attributes can
            go higher I suppose, but it's better to leave them at 4 and just increase the
            weight.
            
            Be very careful if not normalizing, as you can end up with VERY high scores. The
            only attributes that could probably get away with this are things like # of parking
            spaces or bedrooms.
        zero_pt (float, optional): If *norm_by*, percentage at which to set the zero value.
            Defaults to 0.

            Anything left of the zero point (when ascending) or right of it (when descending)
            becomes negative and subtracts from a score, rather than just being lower.

            Finding a good zero point percentage is as easy as:
                ``x = (zerovalue - min) / (max - min)``      # for ascending, setting from left
                ``x = 1 - (zerovalue - min) / (max - min)``  # for descending, setting from right
        **kwargs: To accept non-parameters items from the scorecard dictionary.
            Namely, the *value_keys* tuple for getting the house's attribute value.

    Examples:
        For scoring the listing price, where lower prices are better, and I reasonably
        expect all my prices to be within 275k and 550k:
        >>> import numpy as np
        >>> prices = np.array([350e3, 400e3, 450e3, 500e3])
        >>> continuous_score(prices, 275e3, 550e3, weight=3, ascending=False, norm_by=10)
        array([7.2, 5.4, 3.6, 1.8])

        Set the zero point at 50% so that the upper half of the price scale becomes
        negative:
        >>> continuous_score(prices, 275e3, 550e3, weight=3, ascending=False,
        ...     norm_by=10, zero_pt=.5)
        array([ -7.8,  -9.6, -11.4, -13.2])

        An ascending example, as with the number of bedrooms. Zero point set to
        illustrate that 2 beds is expected, more is increasingly better, but 1 is
        unacceptable and should subtract from the overall score so as to disqualify it.
        >>> beds = np.array([1, 2, 3, 4, 5])
        >>> continuous_score(beds, 1, 5, weight=1, ascending=True, norm_by=4, zero_pt=.2)
        array([-0.8,  0. ,  0.8,  1.6,  2.4])

    Returns:
        float: Score of the value passed.
            Can return an array of scores if the input is also an array of values, but that is
            generally reserved for testing out weights/normalization factors/zero points and not
            for actual usage against a listing.

    Raises:
        ValueError: When the field (i.e. attribute) wasn't found in the listing dictionary for the
            particular house (``dict.get()`` returned None and passed it to this function as
            *value*).

    """
    if value is None:
        raise ValueError('\tNo value passed to scoring function.')

    spread = (max_value - min_value) + 1
    if spread < 50:
        num = spread
    else:
        num = 50
    a = np.linspace(min_value, max_value, num=num)

    if ascending:
        score = np.searchsorted(a, value, side='left')
    else:
        score = np.searchsorted(-a[::-1], -value, side='right')

    # multiply it by (x/50) to normalize on a 0-3.5 scale (or whatever scale specified)
    score = (score * (norm_by / num) - (zero_pt * norm_by)) * weight
    return score.round(1)


def all_continuous_scoring(dic, house_sc, cont_sc):
    """Loops through part 2 of the scorecard, passing arguments to :func:`continuous_score`.

    Uses ``dict.get()`` to avoid KeyErrors if the attribute field is not in the house dict.
    If it's not, prints the error and moves on without scoring it.

    Args:
        dic (dict): House listing.
        house_sc (dict): Scorecard being updated for individual house listing.
        cont_sc (dict): Continuous scoring criteria dictionaries.
            For each criteria (subdict) in this dict, unpack the values to use as the
            arguments to :func:`continuous_score`.

    """
    for score_field, sc in cont_sc.items():
        # Get house value from house dict, assign back to scorecard dict
        sc['value'] = dic[sc['value_keys'][0]].get(sc['value_keys'][1])
        try:
            house_sc[score_field] = continuous_score(**sc)
        except ValueError as e:
            #print(f'{score_field}: {e}')
            continue


def score_laundry(dic, house_sc):
    """Add points if laundry info is available.

    Weighted low because the data is not always provided.
    """
    laundry = False
    appliances = dic['building information'].get('Appliances')
    if appliances is None:
        return
    elif 'washer' in [x.lower() for x in appliances]:
        laundry = True
    elif any([x for x in appliances if 'dryer' in x.lower()]):
        laundry = True
    elif dic['building information'].get('Laundry Type') is not None:
        laundry = True

    if laundry:
        house_sc['laundry_score'] = 2


def sum_scores(house_sc):
    """Sum all scores in the scorecard."""
    total = 0
    item_list = [x for x in house_sc.keys() if x != 'MLS Number']
    for k in item_list:
        try:
            total += house_sc[k]
        except TypeError:
            continue
    house_sc['TOTAL_SCORE'] = round(total, 1)


def write_scorecards_to_file(cards):
    """Combine scorecard(s) and write to single file.
    
    Args:
        cards: A single house scorecard or list of scorecards.
    
    """
    if isinstance(cards, dict):
        cards = [cards]
    json_output_file = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'scorecards.json')
    with open(json_output_file, 'w') as f:
        f.write(json.dumps(cards, indent=4))
    print('Scorecards written to {}'.format(json_output_file))


def score_dict_list_to_dataframe(sc_list):
    """Create a dataframe of a list of scorecards.

    Args:
        sc_list (list): Collection of scorecards as dicts.

    Returns:
        pd.DataFrame

    """
    full_df = pd.DataFrame()
    for sc in sc_list:
        df = pd.DataFrame.from_dict(sc, orient='index').T.set_index('MLS Number')
        full_df = pd.concat([full_df, df], axis=0, sort=False)
    # Rename column headers from their MLS number to their order in the file
    # TODO: don't know what happened to this, but still useful when all the scorecards are for the same house
    return full_df


def write_score_percentiles_to_jsons(sc_list_path=None):
    """With recently created scorecards, write total score & percentile back to listing file.

    Must be run after all scorecards have been generated and written to file. Only then can it
    write each total_score back to _metadata as well as its *k*\ :sup`th` percentile.

    Args:
        sc_list_path (str, optional): Path to ``scorecards.json``. Defaults to ``None``.
            Optional because the code knows where the file should be relative to the rest of the
            project structure. It should have been generated just microseconds prior to this
            function executing, after all.

    """
    if sc_list_path is None:
        sc_list_path = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'scorecards.json')
    scorecards = json_handling.read_dicts_from_json(sc_list_path)

    # Collect all total scores for percentile
    all_scores = np.array([])
    for card in scorecards:
        all_scores = np.append(all_scores, card.get('TOTAL_SCORE'))

    for f in glob.glob(Code.LISTINGS_GLOB):
        house = json_handling.read_dicts_from_json(f)[0]
        mls = house['basic info'].get('MLS Number')
        for card in scorecards:
            if card.get('MLS Number') == mls:
                score = card.get('TOTAL_SCORE')
                modify.update_house_dict(house, ('_metadata', 'total_score'), score)
                percentile = stats.percentileofscore(all_scores, score)
                pct_str = 'higher than {:.0f}% of listings'.format(percentile)
                modify.update_house_dict(house, ('_metadata', 'percentile'), pct_str)
        _ = json_handling.add_dict_to_json(house)


def score_all():
    """Score all the house listings saved in the ``saved_listings`` folder."""
    my_scorecard = get_scorecard(mode='regular')
    my_cont_scorecard = get_scorecard(mode='continuous')

    house_sc_list = []  # for JSON output
    for house_file in glob.glob(Code.LISTINGS_GLOB):
        house_dict = json_handling.read_dicts_from_json(house_file)[0]
        house_sc = score_house_dict(house_dict, my_scorecard, my_cont_scorecard)
        house_sc_list.append(house_sc)

    write_scorecards_to_file(house_sc_list)
    write_score_percentiles_to_jsons()


def sample():
    my_scorecard = get_scorecard(mode='regular')
    my_cont_scorecard = get_scorecard(mode='continuous')
    sample_fname = '4304_34TH_ST_S_B2.json'
    sample_path = os.path.join(Code.LISTINGS_DIR, sample_fname)
    sample_house = json_handling.read_dicts_from_json(sample_path)[0]

    sample_house_sc = score_house_dict(sample_house, my_scorecard, my_cont_scorecard)

    write_scorecards_to_file(sample_house_sc)
    sample_df = score_dict_list_to_dataframe([sample_house_sc])
    print(sample_df.T)


if __name__ == '__main__':
    score_all()
    # sample()
