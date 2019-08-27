"""Clean a dictionary of listing details."""

import time
import glob
import Code
from Code import json_handling, scrape2


def convert_currency_to_int(s):
    try:
        return int(s.strip().replace('$', '').replace(',', ''))
    except AttributeError:
        return int(s)


def parse_string_int(s):
    try:
        return int(s.split()[0])
    except AttributeError:
        return int(s)


def parse_string_float(s):
    try:
        return float(s.split()[0])
    except AttributeError:
        return float(s)


def parse_date(s):
    return time.strptime(s, '%m/%d/%Y')


def keep_string(s):
    return str(s)


currency_list = [
    ('info', 'list_price'),
    ('info', 'sale_price'),
    ('basic info', 'Price Per SQFT'),
    ('basic info', 'HOA Fee'),
    ('building information', 'Price Per SQFT'),
    ('association / location / schools', 'Condo/Coop Fee')
]
int_parse_list = [
    ('info', 'beds'),
    ('info', 'sqft')
]
float_parse_list = [
    ('info', 'baths'),
    ('basic info', 'Lot Size Acres'),
    ('exterior information', 'Lot Size Acres'),
    ('expenses / taxes', 'Tax Annual Amount')
]
date_list = [
    ('info', 'sold')
]
string_list = [
    ('basic info', 'MLS Number')
]


def clean_one(dic):
    """Apply all cleanings to dictionary."""
    for k1, v1 in dic.items():
        for k2, v2 in v1.items():
            if k2 in [x[1] for x in currency_list]:
                v1[k2] = convert_currency_to_int(v2)
            elif k2 in [x[1] for x in int_parse_list]:
                v1[k2] = parse_string_int(v2)
            elif k2 in [x[1] for x in float_parse_list]:
                v1[k2] = parse_string_float(v2)
            #elif k2 in [x[1] for x in date_list]:
            #    v1[k2] = parse_date(v2)
            elif k2 in [x[1] for x in string_list]:
                v1[k2] = keep_string(v2)
            else:
                try:
                    v1[k2] = int(v2)
                except (ValueError, TypeError):  # string, or a tuple
                    continue


if __name__ == '__main__':
    #dic1 = json_to_pandas.sample()
    #clean_one(dic1)

    for f in glob.glob(Code.LISTINGS_GLOB):
        house = json_handling.read_dicts_from_json(f)[0]
        clean_one(house)
        _ = json_handling.add_dict_to_json(house)
