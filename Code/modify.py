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
import Code
from Code import json_handling, support
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
    """Add the bing transit time to listing dict"""
    key_name = 'Work commute (Bing)'
    # Check for existing value
    bingtime = dic['local travel'].setdefault(key_name, None)
    if (bingtime is None) or force:
        house_coords = dic['_metadata']['geocoords']
        try:
            bingtime = bing.get_bing_commute_time(house_coords, keys.work_coords)
        except BadResponse as e:
            print('Could not retrieve commute time for this address.')
            print(e)
            bingtime = None
        finally:
            update_house_dict(dic, ('local travel', key_name), bingtime)


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
        'Lot Features'
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


def sale_price_diff(dic):
    """Update sale price diff"""
    list_price = dic['_info']['list_price']
    sale_price = dic['_info']['sale_price']
    diff = sale_price - list_price
    dic['_info']['sale_price_diff'] = diff
    dic['_info']['sale_diff_pct'] = '{:+.1%}'.format(diff / list_price)


def add_tether(dic):
    """Add straight-line distance to centerpoint (Arlington Cememtery)."""
    house_coords = dic['_metadata'].get('geocoords')
    center = keys.centerpoint
    try:
        dist = support.haversine(house_coords, center)
    except TypeError:
        print('\tDistance from center not added; missing house coords.')
    update_house_dict(dic, ('quickstats', 'tether'), round(dist, 2))


def modify_one(house, loop=False):
    # Add modifying functions here:
    add_coords(house)
    split_comma_delimited_fields(house)
    try:
        # add_citymapper_commute(house)
        pass
    except citymapper.Sleepytime:
        if loop:
            print('sleeping for 90 seconds.')
            sleep(90)
        else:
            pass
    add_bing_commute(house)
    add_nearest_metro(house)
    add_frequent_driving(house, keys.favorites_driving)
    travel_quick_stats(house)
    try:
        sale_price_diff(house)
    except KeyError:
        pass
    add_tether(house)

    remove_key(house, 'basic_info', level=1)
    remove_key(house, 'open houses', level=1)

    # Write back out
    _ = json_handling.add_dict_to_json(house)


def modify_all():
    for f in glob.glob(Code.LISTINGS_GLOB):
        print(os.path.basename(f))
        filepath = os.path.join(Code.LISTINGS_DIR, f)
        house = json_handling.read_dicts_from_json(filepath)[0]
        modify_one(house, loop=True)


if __name__ == '__main__':
    modify_all()
    sample_path = os.path.join(Code.LISTINGS_DIR, '4304_34TH_ST_S_B2.json')
    sample_path = os.path.join(Code.LISTINGS_DIR, '10217_ROLLING_GREEN_WAY.json')
    sample_house = json_handling.read_dicts_from_json(sample_path)[0]
    # modify_one(sample_house)
