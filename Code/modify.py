"""
Module for modifying the contents of a house listing dictionary.

Most often they come directly from scrape2.py, or are read in
from a locally saved JSON file via functions in json_handling.py.

The majority of these functions are dedicated to adding the values
and attributes that come from external data sources, or else are
transformations of existing attributes, post-scraping.
"""
import os
import glob
from time import sleep
from datetime import datetime as dt

import Code
from Code import json_handling, support, clean
from Code.api_calls import bing, citymapper, keys
from Code.support import BadResponse


def update_house_dict(dic, keys_tuple, value):
    """Safely add or update any value in house dict.

    Args:
        dic (dict): house dictionary
        keys_tuple (tuple): a tuple of (category, field)
        value (str, int, float, iterable): whatever's being stored

    """
    # Check if outer key (category) exists; if not, create it
    dic.setdefault(keys_tuple[0], {})
    # Update with new {field: value}
    dic[keys_tuple[0]].update({keys_tuple[1]: value})


def rename_key(dic, old, new, level):
    if level == 1:
        dic[new] = dic.pop(old)
    elif level == 2:
        for k, v in dic.items():
            try:
                v[new] = v.pop(old)
            except KeyError:
                continue
    else:
        raise ValueError("Not a valid level in the dictionary.")


def remove_key(dic, key, level):
    """Remove a key from the listing dict. Use sparingly."""
    if level == 1:
        try:
            dic.pop(key)
            print('\tRemoved: {} from level {}'.format(key, level))
        except KeyError:
            pass
    elif level == 2:
        for k, v in dic.items():
            try:
                v.pop(key)
                print("\tRemoved: '{}' from level {}".format(key, level))
            except KeyError:
                continue
    else:
        raise ValueError("Not a valid level in the dictionary.")


def add_coords(dic, force=False):
    """Add geocoords to house dictionary"""
    # Check for existing value
    coords = dic['_metadata'].setdefault('geocoords', None)
    if (coords is None) or force:
        # Grab coordinates from Bing
        addr = dic['_info']['full_address']
        try:
            coords = bing.get_coords(addr, zip_code=addr[-5:])
        except BadResponse as e:
            print('Could not retrieve geocoords for this address.')
            print(e)
            coords = None
        update_house_dict(dic, ('_metadata', 'geocoords'), coords)


def add_citymapper_commute(dic, force=False):
    """Add the citymapper transit time for work to the listing dict.

    Raises a sleep reminder exception because of the API limits. When
    using this function on a single listing, catch the exception but
    let it pass. However, when running in a loop of multiple listings,
    catch it and let the program sleep for 90 seconds.
    """
    key_name = 'Work commute (Citymapper)'
    # Check for existing value
    cmtime = dic['local travel'].setdefault(key_name, None)
    if (cmtime is None) or force:
        house_coords = dic['_metadata']['geocoords']
        try:
            cmtime = citymapper.get_citymapper_commute_time(house_coords, keys.work_coords)
        except BadResponse as e:
            print(e)
            cmtime = None
        finally:
            update_house_dict(dic, ('local travel', key_name), cmtime)
            raise citymapper.Sleepytime


def add_bing_commute(dic, force=False):
    """Add the bing transit time to listing dict."""
    # Checks for existing values
    key_name_dict = {
        'Work commute (Bing)': dic['local travel'].setdefault('Work commute (Bing)', None),
        'first_walk_mins': dic['quickstats'].setdefault('first_walk_mins', None)
    }
    if (not all([v for k, v in key_name_dict.items()])) | force:
        # At least one of them is empty or force=True, Bing API call is necessary
        # If not force, and if all values exist, then end function
        house_coords = dic['_metadata']['geocoords']
        try:
            commute_time, first_walk_time, first_leg = bing.get_bing_commute_time(house_coords, keys.work_coords)
        except BadResponse as e:
            print('Could not retrieve commute time for this address.')
            print(e)
            commute_time, first_walk_time, first_leg = None, None, None
        finally:
            update_house_dict(dic, ('local travel', 'Work commute (Bing)'), commute_time)
            update_house_dict(dic, ('quickstats', 'first_walk_mins'), round(first_walk_time, 1))
            update_house_dict(dic, ('quickstats', 'first_leg_type'), first_leg)


def add_nearest_metro(dic, force=False):
    """Add the three nearest metro stations in distance order"""
    # Check for existing value
    station_list = dic['local travel'].setdefault('Nearby Metro', None)
    if (station_list is None) or force:
        house_coords = dic['_metadata']['geocoords']
        try:
            station_list = bing.find_nearest_metro(house_coords)
        except BadResponse as e:
            print(e)
            station_list = None
        finally:
            update_house_dict(dic, ('local travel', 'Nearby Metro'), station_list)
    update_house_dict(dic, ('basic info', 'Nearest Metro'), station_list[0][0])


def add_frequent_driving(dic, favorites_dic, force=False):
    """Add the road distance and drive time to frequented places by car."""
    house_coords = dic['_metadata']['geocoords']
    for place, attribs in favorites_dic.items():
        # Check for existing value
        place_coords = dic['local travel'].setdefault(place, None)
        if (place_coords is None) or force:
            place_coords = bing.get_coords(attribs['addr'])
            day = attribs.get('day', None)
            starttime = attribs.get('time', None)
            try:
                distance, duration = bing.get_driving_info(house_coords, place_coords, day, starttime)
            except BadResponse:
                distance, duration = None
            finally:
                update_house_dict(dic, ('local travel', place), (distance, duration))


def travel_quick_stats(dic):
    """Convert some Local Travel numbers for easier scoring."""
    # Grab top metro station's time
    metro = dic['local travel'].get('Nearby Metro')  # returns list of multiple [station, (dist, time)]
    metro_mins = support.str_time_to_min(metro[0][1][1])  # subscripting: first station > values tuple > time

    # Grab bing commute time
    commute = dic['local travel'].get('Work commute (Bing)')
    commute_mins = support.str_time_to_min(commute)

    # Add to new dict
    update_house_dict(dic, ('quickstats', 'metro_walk_mins'), round(metro_mins, 1))
    update_house_dict(dic, ('quickstats', 'commute_transit_mins'), round(commute_mins, 1))


def add_tether(dic):
    """Add straight-line distance to centerpoint (Arlington Cememtery)."""
    house_coords = dic['_metadata'].get('geocoords')
    center = keys.centerpoint
    try:
        dist = support.haversine(house_coords, center)
    except TypeError:
        print('\tDistance from center not added; missing house coords.')
    update_house_dict(dic, ('quickstats', 'tether'), round(dist, 2))


def update_days_on_market(dic):
    """Calculate days from initial listing to last modification date of dict."""
    start_date, end_date = None, dt.today()
    # Find day of initial listing
    for date, text in dic['listing history'].items():
        if 'Sold' in text:
            end_date = dt.strptime(date, '%b %d, %Y')
        elif 'Initial' in text:
            start_date = dt.strptime(date, '%b %d, %Y')
    try:
        dom = (end_date - start_date).days
    except TypeError:
        print('\tListing date not found in history.')
        return
    update_house_dict(dic, ('_metadata', 'days_on_market'), dom)


def change_from_initial(dic):
    """Calculate the change from the initial price."""
    # Get current price
    current_price = dic['_info'].get('list_price')

    # Find initial listing
    for date, text in dic['listing history'].items():
        if 'Initial' in text:
            initial_price = text.split()[3]
            initial_price = clean.convert_currency_to_int(initial_price)

    price_diff = current_price - initial_price
    if price_diff != 0:
        pct_change = '{:+.1%}'.format(price_diff / initial_price)
        update_house_dict(dic, ('_info', 'change'), price_diff)
        update_house_dict(dic, ('_info', 'pct_change'), pct_change)


def sale_price_diff(dic):
    """Get the difference between listing price and sale price."""
    info = dic['_info']
    if info.get('badge') == 'Sold':
        list_price = info.get('list_price')
        sale_price = info.get('sale_price')
        diff = sale_price - list_price
        diff_pct = '{:.1%}'.format(diff / list_price)

        update_house_dict(dic, ('_info', 'sale_price_diff'), diff)
        update_house_dict(dic, ('_info', 'sale_diff_pct'), diff_pct)


def tax_assessed_diff(dic):
    """Get the difference between listing price and the tax assessed value."""
    list_price = dic['_info'].get('list_price')
    tax_assessed = dic['expenses / taxes'].get('Tax Assessed Value')
    diff = tax_assessed - list_price
    diff_pct = '{:.1%}'.format(diff / list_price)

    update_house_dict(dic, ('expenses / taxes', 'tax_assessed_diff'), diff_pct)


def modify_one(house, loop=False):
    # Add modifying functions here:
    add_coords(house)
    try:
        # add_citymapper_commute(house)
        pass
    except citymapper.Sleepytime:
        if loop:
            print('sleeping for 90 seconds.')
            sleep(90)
        else:
            pass
    add_bing_commute(house, force=True)
    add_nearest_metro(house, force=True)
    add_frequent_driving(house, keys.favorites_driving)
    travel_quick_stats(house)
    sale_price_diff(house)
    add_tether(house)
    update_days_on_market(house)
    change_from_initial(house)
    tax_assessed_diff(house)

    # Write back out
    _ = json_handling.add_dict_to_json(house)


def modify_all():
    for f in glob.glob(Code.LISTINGS_GLOB):
        print(os.path.basename(f))
        filepath = os.path.join(Code.LISTINGS_DIR, f)
        house = json_handling.read_dicts_from_json(filepath)[0]
        modify_one(house, loop=True)


if __name__ == '__main__':
    #modify_all()
    sample_path = os.path.join(Code.LISTINGS_DIR, '3417_WELTHAM_ST.json')
    sample_house = json_handling.read_dicts_from_json(sample_path)[0]
    modify_one(sample_house)
