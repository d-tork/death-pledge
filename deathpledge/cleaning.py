"""Clean a dictionary of listing details."""

from datetime import datetime
import logging
import usaddress
from collections import defaultdict

logger = logging.getLogger(__name__)


def split_comma_delimited_fields(home):
    """Create lists out of comma-separated values in certain fields."""
    field_list = [
        ('association_location_schools', 'hoa_condo_coop_amenities'),
        ('association_location_schools', 'hoa_condo_coop_fee_includes'),
        ('building_information', 'appliances'),
        ('building_information', 'interior_features'),
        ('building_information', 'room_list'),
        ('building_information', 'exterior_features'),
        ('building_information', 'garage_feature'),
        ('building_information', 'lot_features'),
        ('building_information', 'basement_type'),
        ('building_information', 'wall_ceiling_types'),
        ('building_information', 'accessibility_features'),
        ('building_information', 'utilities'),  # may have permanently moved
        ('building_information', 'property_condition'),
        ('building_information', 'security_features'),
        ('utilities', 'utilities'),
    ]
    for subdict, key in field_list:
        try:
            listlike_field = home[subdict][key]
        except KeyError:  # field not in dict
            continue
        try:
            value_list = listlike_field.split(', ')
        except AttributeError:  # listlike_field is not a string
            continue
        # Remove 'and' in final element
        value_list[-1] = value_list[-1].replace('and ', '')
        # Replace original value
        home[subdict][key] = value_list


def convert_numbers(home):
    """Parse a float from strings containing currencies and commas."""

    def parse_number(s):
        return float(s.split()[0].replace(',', '').replace('$', '').replace('+', ''))

    numeric_field_list = [
        # Currencies
        ('listing', 'list_price'),
        ('listing', 'sale_price'),
        ('listing', 'price_per_sqft'),
        ('association_location_schools', 'hoa_fee'),
        ('association_location_schools', 'condo_coop_fee'),
        ('listing', 'expenses_taxes', 'tax_annual_amount'),
        ('listing', 'expenses_taxes', 'county_tax'),
        ('listing', 'expenses_taxes', 'tax_assessed_value'),
        ('listing', 'expenses_taxes', 'citytown_tax'),
        # Integers
        ('main', 'beds'),
        ('main', 'sqft'),
        ('exterior_information', 'lot_size_sqft'),
        ('listing', 'expenses_taxes', 'tax_year'),
        # Floats
        ('main', 'baths'),
        ('exterior_information', 'lot_size_acres'),
    ]
    # Enumerated fields
    for key_tuple in numeric_field_list:
        if len(key_tuple) == 2:
            subdict, field = key_tuple
            try:
                val = home[subdict][field]
            except (KeyError, AttributeError) as e:
                continue
            home[subdict][field] = parse_number(val)
        else:
            subdict1, subdict2, field = key_tuple
            try:
                val = home[subdict1][subdict2][field]
            except (KeyError, AttributeError) as e:
                continue
            home[subdict1][subdict2][field] = parse_number(val)
    # All numbers in building_information

    try:
        for k, v in home['building_information'].items():
            try:
                home['building_information'][k] = int(v)
            except (ValueError, TypeError):  # individual field not a number
                continue
    except KeyError:  # No building_information
        pass


def convert_dates(home):
    def parse_date(s):
        return str(datetime.strptime(s, '%m/%d/%Y'))

    date_list = [
        ('listing', 'sold')
    ]
    for key_tuple in date_list:
        subdict, field = key_tuple
        try:
            val = home[subdict][field]
        except KeyError as e:
            continue
        try:
            home[subdict][field] = parse_date(val)
        except AttributeError:  # likely already a date object
            continue


def remove_dupe_fields(home):
    dupe_fields = [
        ('building_information', 'price_per_sqft'),  # found in basic_info, moved to listing
        ('basic_info', 'lot_size_acres'),  # found in exterior_information
        ('listing', 'tax_annual_amount'),  # found in expenses_taxes
        ('basic_info', 'structure_type'),  # found in building_information
        ('basic_info', 'architectural_style'),  # found in building_information
        ('basic_info', 'year_built'),  # found in building_information
        ('basic_info', 'hoa_fee'),  # found in association_location_schools
        ('basic_info', 'county'),  # found in association_location_schools
    ]
    for key_tuple in dupe_fields:
        subdict, field = key_tuple
        try:
            del home[subdict][field]
        except KeyError as e:
            continue


def parse_address(home):
    """Split address into parsed fields."""
    full_address = home['main']['full_address']
    addr_tuples = usaddress.parse(full_address)
    parsed = defaultdict(list)  # format as proper dict
    for v, k in addr_tuples:
        v = v.replace(',', '')  # remove comma from city name
        parsed[k].append(v)  # for multi-word values belonging to same key
    parsed = {k: ' '.join(v) for k, v in parsed.items()}
    home['main']['parsed_address'] = parsed
