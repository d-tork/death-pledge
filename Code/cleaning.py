"""Clean a dictionary of listing details."""

import time
import logging

logger = logging.getLogger(__name__)


def split_comma_delimited_fields(dic):
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
        ('building_information', 'utilities'),
    ]
    for subdict, key in field_list:
        try:
            listlike_field = dic[subdict][key]
            value_list = listlike_field.split(', ')
        except Exception as e:
            logger.info(f'{dic["main"]["address"]} - Failed to split ({subdict}, {key}) into list.')
            continue
        # Remove 'and' in final element
        value_list[-1] = value_list[-1].replace('and ', '')
        # Replace original value
        dic[subdict][key] = value_list


def convert_numbers(dic):
    """Parse a float from strings containing currencies and commas."""
    def parse_number(s):
        return float(s.split()[0].replace(',', '').replace('$', ''))

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
        ('basic_info', 'lot_size_acres'),
        ('exterior_information', 'lot_size_acres'),
    ]
    # Enumerated fields
    for key_tuple in numeric_field_list:
        if len(key_tuple) == 2:
            subdict, field = key_tuple
            try:
                val = dic[subdict][field]
            except KeyError as e:
                logger.info(f'{dic["main"]["address"]} - Subdict or field does not exist: {e}')
                continue
            dic[subdict][field] = parse_number(val)
        else:
            subdict1, subdict2, field = key_tuple
            try:
                val = dic[subdict1][subdict2][field]
            except KeyError as e:
                logger.info(f'{dic["main"]["address"]} - One or more subdicts or fields do not exist: {e}')
                continue
            dic[subdict1][subdict2][field] = parse_number(val)
    # All numbers in building_information
    for k, v in dic['building_information'].items():
        try:
            dic['building_information'][k] = int(v)
        except (ValueError, TypeError):  # not a number
            pass


def convert_dates(dic):
    def parse_date(s):
        return time.strptime(s, '%m/%d/%Y')
    date_list = [
        ('listing', 'sold')
    ]
    for key_tuple in date_list:
        subdict, field = key_tuple
        try:
            val = dic[subdict][field]
        except KeyError as e:
            logger.info(f'{dic["main"]["address"]} - Subdict or field does not exist: {e}')
            continue
        dic[subdict][field] = parse_date(val)


def remove_dupe_fields(dic):
    dupe_fields = [
        ('building_information', 'price_per_sqft'),  # found in basic_info, moved to listing
        ('basic_info', 'lot_size_acres'),            # found in exterior_information
        ('listing', 'tax_annual_amount'),            # found in expenses_taxes
        ('basic_info', 'structure_type'),            # found in building_information
        ('basic_info', 'architectural_style'),       # found in building_information
        ('basic_info', 'year_built'),                # found in building_information
        ('basic_info', 'hoa_fee'),                   # found in association_location_schools
        ('basic_info', 'county'),                    # found in association_location_schools
    ]
    for key_tuple in dupe_fields:
        subdict, field = key_tuple
        try:
            del dic[subdict][field]
        except KeyError as e:
            logger.info(f'{dic["main"]["address"]} - Subdict or field does not exist: {e}')
            continue


