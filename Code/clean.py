"""Clean a dictionary of listing details."""

import time


def convert_currency_to_int(s):
    try:
        return int(s.strip().replace('$', '').replace(',', ''))
    except AttributeError:
        return int(s)


def parse_string_int(s):
    try:
        return int(s.split()[0].replace(',', ''))
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


def split_comma_delimited_fields(dic):
    """Create lists out of comma-separated values in certain fields."""
    field_list = [
        'HOA/Condo/Coop Amenities',
        'HOA/Condo/Coop Fee Includes',
        'Appliances',
        'Interior Features',
        'Room List',
        'Exterior Features',
        'Garage Features',
        'Lot Features',
        'Basement Type',
        'Wall & Ceiling Types',
        'Accessibility Features',
        'Utilities',
    ]
    for k1, v1 in dic.items():
        for field in [x for x in field_list if x in v1]:
            try:
                val_list = v1[field].split(', ')
            except AttributeError:  # no longer a string
                continue
            # Replace 'and' in final element
            val_list[-1] = val_list[-1].replace('and ', '')
            v1[field] = val_list


currency_list = [
    ('_info', 'list_price'),
    ('_info', 'sale_price'),
    ('basic info', 'Price Per SQFT'),
    ('basic info', 'HOA Fee'),
    ('building information', 'Price Per SQFT'),
    ('association / location / schools', 'Condo/Coop Fee'),
    ('expenses / taxes', 'Tax Annual Amount')
]
int_parse_list = [
    ('_info', 'beds'),
    ('_info', 'sqft')
]
float_parse_list = [
    ('_info', 'baths'),
    ('basic info', 'Lot Size Acres'),
    ('exterior information', 'Lot Size Acres'),
]
date_list = [
    ('_info', 'sold')
]
string_list = [
    ('basic info', 'MLS Number')
]


def clean_one(dic):
    """Apply all cleanings to dictionary."""
    split_comma_delimited_fields(dic)
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

