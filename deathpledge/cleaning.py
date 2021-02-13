"""Clean a dictionary of listing details."""

import logging
import usaddress
from collections import defaultdict

from deathpledge import TIMEFORMAT, support

logger = logging.getLogger(__name__)


def split_comma_delimited_fields(home):
    """Create lists out of comma-separated values in certain fields."""
    field_list = [
        'hoa_condo_coop_amenities',
        'hoa_condo_coop_fee_includes',
        'appliances',
        'interior_features',
        'room_list',
        'exterior_features',
        'garage_feature',
        'lot_features',
        'basement_type',
        'wall_ceiling_types',
        'accessibility_features',
        'utilities',  # may have permanently moved
        'property_condition',
        'security_features',
        'utilities',
    ]
    for key in field_list:
        try:
            listlike_field = home[key]
        except KeyError:  # field not in dict
            continue
        try:
            value_list = listlike_field.split(', ')
        except AttributeError:  # listlike_field is not a string
            continue
        # Remove 'and' in final element
        value_list[-1] = value_list[-1].replace('and ', '')
        # Replace original value
        home[key] = value_list
        logger.debug(f'Field {key} split into list items')


def parse_number(s):
    return float(s.split()[0].replace(',', '').replace('$', '').replace('+', ''))


def convert_numbers(home):
    """Parse a float from strings containing currencies and commas."""
    numeric_field_list = [
        # Currencies
        'list_price',
        'sale_price',
        'price_per_sqft',
        'price_sqft',
        'total_taxes',
        'county_tax',
        'tax_value',
        'city_tax',
        'school_tax',
        'estimated_value',
        # Integers
        'beds',
        'sqft',
        'lot_size_sqft',
        'tax_year',
        # Floats
        'baths',
        'lot_size_acres',
    ]
    for key in numeric_field_list:
        try:
            val = home[key]
        except KeyError:
            continue
        else:
            try:
                home[key] = parse_number(val)
            except AttributeError:
                continue
            else:
                logger.debug(f'Field {key} converted to number')


def split_fee_frequency(home):
    """Parses HOA/Co-op fee and frequency."""
    fee_fields = ['hoa_fee', 'condocoop_fee']
    for key in fee_fields:
        try:
            val = home[key]
        except KeyError:
            continue
        try:
            fee, freq = val.split('/')
        except (AttributeError, ValueError):
            logger.exception(f'Failed to split {key}: {val}')
        else:
            home[key] = parse_number(fee)
            home[f'{key}_frequency'] = freq
            logger.debug(f'Field {key} split and converted')


def parse_address(home):
    """Split address into parsed fields."""
    full_address = home['full_address']
    addr_tuples = usaddress.parse(full_address)
    parsed = defaultdict(list)  # format as proper dict
    for v, k in addr_tuples:
        v = v.replace(',', '')  # remove comma from city name
        parsed[k].append(v)  # for multi-word values belonging to same key
    parsed = {k: ' '.join(v) for k, v in parsed.items()}
    home['parsed_address'] = parsed


def parse_homescout_date(home):
    """Convert date when added to homescout."""
    date_added = home['new_on_homescout']
    parsed_datetime = support.coerce_date_string_to_date(date_added)
    formatted_datetime = parsed_datetime.strftime(TIMEFORMAT)
    home['new_on_homescout'] = formatted_datetime
